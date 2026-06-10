"""RAG pipeline for the CULPA professor review guide."""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).parent
DOCUMENTS_DIR = ROOT / "documents"
MANIFEST_PATH = DOCUMENTS_DIR / "culpa_sources_manifest.json"
CHUNKS_PATH = ROOT / "chunks.jsonl"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "culpa_professor_reviews"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_CHUNK_CHARS = 3500

_embedding_model: SentenceTransformer | None = None


def clean_text(value: Any) -> str:
    """Normalize CULPA text fields without changing their meaning."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_manifest() -> list[dict[str, Any]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_raw_reviews(manifest_item: dict[str, Any]) -> list[dict[str, Any]]:
    raw_path = ROOT / manifest_item["raw_json_file"]
    pages = json.loads(raw_path.read_text(encoding="utf-8"))
    reviews: list[dict[str, Any]] = []
    seen_review_ids: set[str] = set()

    for page in pages:
        for review in page.get("payload", {}).get("reviews", []):
            review_id = str(review.get("review_id", ""))
            if review_id and review_id in seen_review_ids:
                continue
            seen_review_ids.add(review_id)
            reviews.append(review)

    return reviews


def split_long_review(text: str) -> list[str]:
    """Split rare long reviews by paragraph with one-paragraph overlap."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []

    for paragraph in paragraphs:
        candidate = "\n\n".join(current + [paragraph]).strip()
        if len(candidate) <= MAX_CHUNK_CHARS:
            current.append(paragraph)
            continue

        if current:
            chunks.append("\n\n".join(current).strip())
            current = current[-1:] + [paragraph]
        else:
            chunks.append(paragraph[:MAX_CHUNK_CHARS].strip())
            remainder = paragraph[MAX_CHUNK_CHARS:].strip()
            current = [remainder] if remainder else []

    if current:
        chunks.append("\n\n".join(current).strip())

    return [chunk for chunk in chunks if chunk]


def review_base_text(professor_name: str, source_document: str, review: dict[str, Any]) -> str:
    course = review.get("course_header") or {}
    course_code = clean_text(course.get("course_code")) or "Unknown course code"
    course_name = clean_text(course.get("course_name")) or "Unknown course name"
    workload = clean_text(review.get("workload")) or "No workload text provided."
    content = clean_text(review.get("content")) or "No review content provided."

    return "\n".join(
        [
            f"Professor: {professor_name}",
            f"Source document: {source_document}",
            f"Review ID: {review.get('review_id', 'Unknown')}",
            f"Submission date: {review.get('submission_date', 'Unknown')}",
            f"Course: {course_code} - {course_name}",
            f"Rating: {review.get('rating', 'Unknown')}/5",
            "",
            "Workload:",
            workload,
            "",
            "Review content:",
            content,
        ]
    ).strip()


def build_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for manifest_item in load_manifest():
        professor_name = manifest_item["professor_name"]
        source_document = Path(manifest_item["document_file"]).name
        public_url = manifest_item["public_url"]
        reviews = load_raw_reviews(manifest_item)

        for review_index, review in enumerate(reviews, start=1):
            course = review.get("course_header") or {}
            full_text = review_base_text(professor_name, source_document, review)
            parts = split_long_review(full_text)

            for part_index, part in enumerate(parts, start=1):
                chunk_number = len(chunks) + 1
                review_id = str(review.get("review_id", f"{professor_name}-{review_index}"))
                chunk_id = f"{manifest_item['professor_id']}-{review_id}-{part_index}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": part,
                        "metadata": {
                            "chunk_number": chunk_number,
                            "professor": professor_name,
                            "professor_id": int(manifest_item["professor_id"]),
                            "source_document": source_document,
                            "source_url": public_url,
                            "review_id": review_id,
                            "review_index": review_index,
                            "part_index": part_index,
                            "course_code": clean_text(course.get("course_code")),
                            "course_name": clean_text(course.get("course_name")),
                            "rating": int(review.get("rating") or 0),
                            "submission_date": clean_text(review.get("submission_date")),
                        },
                    }
                )

    return chunks


def save_chunks(chunks: list[dict[str, Any]], path: Path = CHUNKS_PATH) -> None:
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def chroma_collection(rebuild: bool = False):
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(name=COLLECTION_NAME)


def build_index(rebuild: bool = True) -> list[dict[str, Any]]:
    chunks = build_chunks()
    save_chunks(chunks)

    collection = chroma_collection(rebuild=rebuild)
    model = embedding_model()

    batch_size = 64
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [item["text"] for item in batch]
        embeddings = model.encode(texts, normalize_embeddings=True).tolist()
        collection.add(
            ids=[item["id"] for item in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[item["metadata"] for item in batch],
        )

    return chunks


def retrieve(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    collection = chroma_collection(rebuild=False)
    model = embedding_model()
    query_embedding = model.encode([question], normalize_embeddings=True).tolist()[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: list[dict[str, Any]] = []
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        retrieved.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": float(distance),
            }
        )

    return retrieved


def format_context(chunks: list[dict[str, Any]]) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk["metadata"]
        source = (
            f"{metadata['source_document']} | review {metadata['review_id']} | "
            f"{metadata['course_code']} | distance {chunk['distance']:.3f}"
        )
        blocks.append(f"[Source {index}: {source}]\n{chunk['text']}")
    return "\n\n---\n\n".join(blocks)


def source_lines(chunks: list[dict[str, Any]]) -> list[str]:
    lines = []
    seen = set()
    for chunk in chunks:
        metadata = chunk["metadata"]
        line = (
            f"{metadata['source_document']} | review {metadata['review_id']} | "
            f"{metadata['course_code']} | distance {chunk['distance']:.3f}"
        )
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return lines


def answer_with_groq(question: str, chunks: list[dict[str, Any]]) -> str:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "GROQ_API_KEY is not set. Add it to a local .env file to enable generation. "
            "Retrieved sources are still shown separately."
        )

    context = format_context(chunks)
    system_prompt = (
        "You answer questions about Columbia CS professor reviews using only the "
        "provided CULPA review excerpts. If the excerpts do not contain enough "
        "information, say: \"I don't have enough information from the provided "
        "reviews to answer that.\" Do not use outside knowledge. Cite sources in "
        "the answer using the source numbers provided, such as [Source 1]."
    )
    user_prompt = f"Question: {question}\n\nRetrieved review excerpts:\n{context}"

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=700,
    )
    return response.choices[0].message.content or ""


def ask(question: str, top_k: int = 5) -> dict[str, Any]:
    chunks = retrieve(question, top_k=top_k)
    answer = answer_with_groq(question, chunks)
    return {
        "answer": answer,
        "sources": source_lines(chunks),
        "chunks": chunks,
    }
