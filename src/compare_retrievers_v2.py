import json
from pathlib import Path

from src.policy_retrieval import POLICY_PATH

from src.semantic_retrieval import (
    embed_texts,
    rank_sections,
)

from src.hybrid_retrieval import (
    load_retrievable_sections,
    keyword_rank,
    reciprocal_rank_fusion,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "data/evaluation/real_policy_queries.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/evaluation/retriever_comparison_v2.json"
)


def evaluate_ranked_results(dataset, rankings, top_k):
    """
    Calculate Hit@K and MRR@K from ranked results.
    """

    if not dataset:
        raise ValueError("Dataset cannot be empty")

    hits = []
    reciprocal_ranks = []
    details = []

    for example, ranking in zip(dataset, rankings):
        expected = set(example["relevant_headings"])

        retrieved = [
            item["heading"] for item in ranking[:top_k]
        ]

        first_rank = next(
            (
                rank
                for rank, heading in enumerate(
                    retrieved, start=1
                )
                if heading in expected
            ),
            None,
        )

        hit = int(first_rank is not None)

        rr = (
            1.0 / first_rank
            if first_rank is not None
            else 0.0
        )

        hits.append(hit)
        reciprocal_ranks.append(rr)

        details.append({
            "query": example["query"],
            "expected": sorted(expected),
            "retrieved": retrieved,
            "hit": hit,
            "reciprocal_rank": rr,
        })

    return {
        "hit_rate": sum(hits) / len(hits),
        "mrr": sum(reciprocal_ranks) / len(
            reciprocal_ranks
        ),
        "results": details,
    }


def main():
    dataset = json.loads(
        DATASET_PATH.read_text(encoding="utf-8")
    )

    if not dataset:
        raise ValueError("Evaluation dataset is empty")

    sections = load_retrievable_sections(POLICY_PATH)

    if not sections:
        raise ValueError("No retrievable policy sections")

    headings = [section["heading"] for section in sections]

    if len(headings) != len(set(headings)):
        raise ValueError(
            "Policy section headings must be unique"
        )

    for example in dataset:
        if not example["relevant_headings"]:
            raise ValueError("Missing relevance labels")

        unknown = (
            set(example["relevant_headings"]) - set(headings)
        )

        if unknown:
            raise ValueError(
                f"Unknown relevant headings: {sorted(unknown)}"
            )

    print("Generating policy embeddings...")

    section_texts = [
        section["heading"] + "\n" + section["content"]
        for section in sections
    ]

    section_embeddings = embed_texts(section_texts)

    print("Generating query embeddings...")

    query_embeddings = embed_texts([
        example["query"] for example in dataset
    ])

    rankings = {
        "keyword": [],
        "semantic": [],
        "hybrid": [],
    }

    for example, query_embedding in zip(
        dataset, query_embeddings
    ):
        query = example["query"]

        keyword_results = keyword_rank(
            query,
            sections,
        )

        semantic_results = rank_sections(
            query_embedding,
            sections,
            section_embeddings,
            top_k=len(sections),
        )

        hybrid_results = reciprocal_rank_fusion(
            [keyword_results, semantic_results],
            top_k=len(sections),
        )

        rankings["keyword"].append(keyword_results)
        rankings["semantic"].append(semantic_results)
        rankings["hybrid"].append(hybrid_results)

    report = {
        "embedding_model": "qwen3-embedding:4b",
        "number_of_queries": len(dataset),
        "number_of_sections": len(sections),
        "metrics": {},
    }

    print("\nRESOLVEAI — THREE-WAY RETRIEVAL COMPARISON")
    print("=" * 55)

    for method, method_rankings in rankings.items():
        report["metrics"][method] = {}

        print(f"\n{method.upper()}")

        for top_k in [1, 3]:
            scores = evaluate_ranked_results(
                dataset,
                method_rankings,
                top_k,
            )

            report["metrics"][method][
                f"top_{top_k}"
            ] = scores

            print(
                f"Hit@{top_k}: "
                f"{scores['hit_rate']:.2%}"
            )

            print(
                f"MRR@{top_k}: "
                f"{scores['mrr']:.3f}"
            )

    print("\nTRACKING QUESTION")
    print("-" * 55)

    for index, example in enumerate(dataset):
        if "5. Baggage Tracking" in example[
            "relevant_headings"
        ]:
            print(f"Question: {example['query']}")

            for method in rankings:
                retrieved = [
                    result["heading"]
                    for result in rankings[method][index][:3]
                ]

                print(f"{method}: {retrieved}")

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
