import json
from pathlib import Path

from src.retrieval_evaluation import evaluate_dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent

POLICY_PATH = (
    PROJECT_ROOT
    / "data/evaluation/benchmark_policy.md"
)

DATASET_PATH = (
    PROJECT_ROOT
    / "data/evaluation/policy_queries.json"
)


def main():
    dataset = json.loads(
        DATASET_PATH.read_text(encoding="utf-8")
    )

    report = evaluate_dataset(
        dataset=dataset,
        policy_path=POLICY_PATH,
        top_k=3
    )

    print("\nRESOLVEAI RETRIEVAL EVALUATION")
    print("=" * 40)

    print(
        f"Total queries: {report['total_queries']}"
    )

    print(
        f"Hit@{report['top_k']}: "
        f"{report['hit_rate']:.2%}"
    )

    print(
        f"MRR@{report['top_k']}: "
        f"{report['mrr']:.3f}"
    )

    print("\nQUERY RESULTS")
    print("-" * 40)

    for result in report["results"]:
        print(f"\nQuestion: {result['query']}")

        print(
            "Expected:",
            result["relevant_headings"]
        )

        print(
            "Retrieved:",
            result["retrieved_headings"]
        )

        print(
            "Hit:",
            bool(result["hit"])
        )

        print(
            "Reciprocal rank:",
            round(result["reciprocal_rank"], 3)
        )


if __name__ == "__main__":
    main()
