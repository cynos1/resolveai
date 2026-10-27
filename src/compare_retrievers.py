import json
from pathlib import Path

from src.policy_retrieval import (
    POLICY_PATH,
    search_policy,
)
from src.semantic_retrieval import (
    prepare_policy_embeddings,
    semantic_search,
)
from src.retrieval_evaluation import evaluate_dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "data/evaluation/real_policy_queries.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/evaluation/retriever_comparison.json"
)


def evaluate_rankings(dataset, search_function, top_k=3):
    """Evaluate a retriever from its ranked headings."""

    results = []

    for example in dataset:
        retrieved = search_function(
            example["query"],
            top_k=top_k
        )

        headings = [
            item["heading"] for item in retrieved
        ]

        relevant = set(example["relevant_headings"])

        rank = next(
            (
                index
                for index, heading in enumerate(
                    headings, start=1
                )
                if heading in relevant
            ),
            None
        )

        results.append({
            "query": example["query"],
            "expected": example["relevant_headings"],
            "retrieved": headings,
            "hit": int(rank is not None),
            "reciprocal_rank": (
                1 / rank if rank is not None else 0.0
            )
        })

    count = len(results)

    return {
        "hit_rate": sum(
            result["hit"] for result in results
        ) / count,
        "mrr": sum(
            result["reciprocal_rank"]
            for result in results
        ) / count,
        "results": results
    }


def main():
    dataset = json.loads(
        DATASET_PATH.read_text(encoding="utf-8")
    )

    print("Preparing local policy embeddings...")

    sections, embeddings = prepare_policy_embeddings(
        POLICY_PATH
    )

    keyword_report = evaluate_dataset(
        dataset,
        policy_path=POLICY_PATH,
        top_k=3
    )

    semantic_report = evaluate_rankings(
        dataset,
        search_function=lambda query, top_k: semantic_search(
            query,
            sections,
            embeddings,
            top_k=top_k
        ),
        top_k=3
    )

    print("\nRESOLVEAI RETRIEVAL COMPARISON")
    print("=" * 45)

    print(
        f"Keyword Hit@3: "
        f"{keyword_report['hit_rate']:.2%}"
    )

    print(
        f"Keyword MRR@3: "
        f"{keyword_report['mrr']:.3f}"
    )

    print(
        f"Semantic Hit@3: "
        f"{semantic_report['hit_rate']:.2%}"
    )

    print(
        f"Semantic MRR@3: "
        f"{semantic_report['mrr']:.3f}"
    )

    print("\nSEMANTIC QUERY RESULTS")
    print("-" * 45)

    for result in semantic_report["results"]:
        print(f"\nQuestion: {result['query']}")
        print(f"Expected: {result['expected']}")
        print(f"Retrieved: {result['retrieved']}")
        print(f"Hit: {bool(result['hit'])}")

    comparison = {
        "embedding_model": "qwen3-embedding:4b",
        "top_k": 3,
        "keyword": keyword_report,
        "semantic": semantic_report
    }

    OUTPUT_PATH.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8"
    )

    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
