"""Build chunks and the local ChromaDB index."""

from rag_pipeline import build_index


def main() -> None:
    chunks = build_index(rebuild=True)
    print(f"Built ChromaDB index with {len(chunks)} chunks.")
    print("Saved chunks to chunks.jsonl.")
    print("Saved vector store to chroma_db/.")


if __name__ == "__main__":
    main()
