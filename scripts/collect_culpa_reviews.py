"""Collect CULPA CS professor reviews as local project documents.

This script is for Milestone 1 document collection. It downloads review JSON
from CULPA's public API, saves the raw API responses, and writes one readable
text document per professor under documents/.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://culpa.info/api/review/professor/{professor_id}?page={page}"
PUBLIC_URL = "https://culpa.info/professor/{professor_id}"
MAX_PAGES_PER_PROFESSOR = 50

PROFESSORS = [
    {"id": 515, "name": "Adam Cannon"},
    {"id": 3409, "name": "Paul Blaer"},
    {"id": 13639, "name": "Tony Dear"},
    {"id": 13076, "name": "Ansaf Salleb-Aouissi"},
    {"id": 45, "name": "Jason Nieh"},
    {"id": 1342, "name": "Clifford Stein"},
    {"id": 375, "name": "Luis Gravano"},
    {"id": 3429, "name": "Simha Sethumadhavan"},
    {"id": 1621, "name": "Tal Malkin"},
    {"id": 1724, "name": "Rocco Servedio"},
]


def slugify(value: str) -> str:
    """Convert a professor name into a stable file-friendly slug."""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ai201-unofficial-guide-document-collector/1.0",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while fetching {url}: {exc}") from exc


def collect_professor(professor_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    pages: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    expected_total = 0

    for page in range(1, MAX_PAGES_PER_PROFESSOR + 1):
        url = API_URL.format(professor_id=professor_id, page=page)
        payload = fetch_json(url)
        page_reviews = payload.get("reviews", [])
        expected_total = int(payload.get("number_of_reviews") or expected_total or 0)

        pages.append({"url": url, "payload": payload})

        if not page_reviews:
            break

        reviews.extend(page_reviews)

        if expected_total and len(reviews) >= expected_total:
            break

        time.sleep(0.15)

    return pages, reviews, expected_total


def review_to_text(index: int, review: dict[str, Any]) -> str:
    course = review.get("course_header") or {}
    course_code = course.get("course_code") or "Unknown course code"
    course_name = course.get("course_name") or "Unknown course name"

    lines = [
        f"Review {index}",
        f"Review ID: {review.get('review_id', 'Unknown')}",
        f"Submission date: {review.get('submission_date', 'Unknown')}",
        f"Course: {course_code} - {course_name}",
        f"Rating: {review.get('rating', 'Unknown')}/5",
        (
            "Feedback counts: "
            f"agree={review.get('agree_count', 0)}, "
            f"disagree={review.get('disagree_count', 0)}, "
            f"funny={review.get('funny_count', 0)}"
        ),
        "",
        "Workload:",
        (review.get("workload") or "No workload text provided.").strip(),
        "",
        "Review content:",
        (review.get("content") or "No review content provided.").strip(),
    ]
    return "\n".join(lines)


def write_professor_document(
    output_dir: Path,
    professor: dict[str, Any],
    pages: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    expected_total: int,
) -> dict[str, Any]:
    professor_id = int(professor["id"])
    professor_name = str(professor["name"])
    slug = slugify(professor_name)

    raw_dir = output_dir / "raw_json"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"{slug}.json"
    text_path = output_dir / f"{slug}_reviews.txt"

    raw_path.write_text(json.dumps(pages, indent=2), encoding="utf-8")

    header = [
        f"Professor: {professor_name}",
        f"CULPA professor ID: {professor_id}",
        f"Public page: {PUBLIC_URL.format(professor_id=professor_id)}",
        f"API source pattern: {API_URL.format(professor_id=professor_id, page=1)}",
        f"Total reviews reported by API: {expected_total}",
        f"Reviews collected: {len(reviews)}",
        "",
        "=" * 80,
        "",
    ]

    body = []
    for index, review in enumerate(reviews, start=1):
        body.append(review_to_text(index, review))
        body.append("")
        body.append("-" * 80)
        body.append("")

    text_path.write_text("\n".join(header + body).strip() + "\n", encoding="utf-8")

    return {
        "professor_id": professor_id,
        "professor_name": professor_name,
        "public_url": PUBLIC_URL.format(professor_id=professor_id),
        "api_url_page_1": API_URL.format(professor_id=professor_id, page=1),
        "raw_json_file": str(raw_path.as_posix()),
        "document_file": str(text_path.as_posix()),
        "reported_review_count": expected_total,
        "collected_review_count": len(reviews),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect CULPA professor review documents.")
    parser.add_argument(
        "--output-dir",
        default="documents",
        help="Directory where documents and raw JSON will be saved.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for professor in PROFESSORS:
        professor_id = int(professor["id"])
        professor_name = str(professor["name"])
        print(f"Collecting {professor_name} ({professor_id})...")
        pages, reviews, expected_total = collect_professor(professor_id)
        manifest_item = write_professor_document(output_dir, professor, pages, reviews, expected_total)
        manifest.append(manifest_item)

        if manifest_item["reported_review_count"] != manifest_item["collected_review_count"]:
            print(
                "  Warning: API reported "
                f"{manifest_item['reported_review_count']} reviews but returned "
                f"{manifest_item['collected_review_count']} through pagination."
            )

    manifest_path = output_dir / "culpa_sources_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_reviews = sum(item["collected_review_count"] for item in manifest)
    print(f"Saved {len(manifest)} documents with {total_reviews} total reviews.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
