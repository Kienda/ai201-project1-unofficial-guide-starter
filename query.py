"""Command-line query interface for the CULPA RAG system."""

from __future__ import annotations

import argparse

from rag_pipeline import ask, retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about CULPA CS reviews.")
    parser.add_argument("question", nargs="*", help="Question to ask.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve.")
    parser.add_argument(
        "--retrieve-only",
        action="store_true",
        help="Only print retrieved chunks; do not call Groq.",
    )
    args = parser.parse_args()

    question = " ".join(args.question).strip()
    if not question:
        question = input("Question: ").strip()

    if args.retrieve_only:
        chunks = retrieve(question, top_k=args.top_k)
        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk["metadata"]
            print("=" * 80)
            print(f"Result {index} | distance={chunk['distance']:.3f}")
            print(
                f"Source: {metadata['source_document']} | "
                f"review {metadata['review_id']} | {metadata['course_code']}"
            )
            print("-" * 80)
            print(chunk["text"])
        return

    result = ask(question, top_k=args.top_k)
    print("\nAnswer\n------")
    print(result["answer"])
    print("\nSources\n-------")
    for source in result["sources"]:
        print(f"- {source}")


if __name__ == "__main__":
    main()
