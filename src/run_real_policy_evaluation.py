import json
from pathlib import Path

from src.policy_retrieval import POLICY_PATH
from src.retrieval_evaluation import evaluate_dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "data/evaluation/real_policy_queries.json"
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

    print("\nRESOLVEAI — REAL POLICY EVALUATION")
    print("=" * 45)

    print(f"Queries: {report['total_queries']}")
    print(f"Hit@3: {report['hit_rate']:.2%}")
    print(f"MRR@3: {report['mrr']:.3f}")

    print("\nINDIVIDUAL RESULTS")
    print("-" * 45)

    for result in report["results"]:
        print(f"\nQuery: {result['query']}")
        print(f"Expected: {result['relevant_headings']}")
        print(f"Retrieved: {result['retrieved_headings']}")
        print(f"Hit: {bool(result['hit'])}")
        print(
            f"Reciprocal rank: "
            f"{result['reciprocal_rank']:.3f}"
        )

    output_path = (
        PROJECT_ROOT
        / "data/evaluation/real_policy_results.json"
    )

    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
