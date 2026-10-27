from src.persistent_index import (
    INDEX_PATH,
    get_or_build_index,
    search_persistent_index,
)


def main():
    print("\nRESOLVEAI — PERSISTENT SEMANTIC RETRIEVAL")
    print("=" * 50)

    index, status = get_or_build_index()

    print(f"Index status: {status}")
    print(f"Embedding model: {index['embedding_model']}")
    print(f"Indexed sections: {len(index['sections'])}")
    print(f"Vector dimensions: {index['dimensions']}")
    print(f"Index file: {INDEX_PATH}")

    query = (
        "Can the airline tell me exactly "
        "where my suitcase is right now?"
    )

    print(f"\nQuestion: {query}")

    results = search_persistent_index(
        query,
        index,
        top_k=3,
    )

    print("\nRETRIEVED POLICY EVIDENCE")
    print("-" * 50)

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result['heading']} "
            f"(similarity: {result['score']:.4f})"
        )


if __name__ == "__main__":
    main()
