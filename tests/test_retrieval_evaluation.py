import pytest

from src.retrieval_evaluation import (
    evaluate_query,
    evaluate_dataset
)


@pytest.fixture
def policy(tmp_path):
    path = tmp_path / "test_policy.md"

    path.write_text(
        "# Test Policy\n"
        "\n"
        "## Reporting\n"
        "Report delayed baggage within 24 hours.\n"
        "\n"
        "## Reimbursement\n"
        "Receipts are required for reimbursement.\n"
        "\n"
        "## Approval\n"
        "A human agent approves requests.\n",
        encoding="utf-8"
    )

    return path


def test_relevant_result_is_found(policy):
    result = evaluate_query(
        query="receipts reimbursement",
        relevant_headings=["Reimbursement"],
        policy_path=policy,
        top_k=3
    )

    assert result["hit"] == 1
    assert result["reciprocal_rank"] == 1.0


def test_missing_result_scores_zero(policy):
    result = evaluate_query(
        query="volcano submarine",
        relevant_headings=["Reporting"],
        policy_path=policy,
        top_k=3
    )

    assert result["hit"] == 0
    assert result["reciprocal_rank"] == 0.0


def test_dataset_metrics(policy):
    dataset = [
        {
            "query": "receipts reimbursement",
            "relevant_headings": ["Reimbursement"]
        },
        {
            "query": "volcano submarine",
            "relevant_headings": ["Reporting"]
        }
    ]

    report = evaluate_dataset(
        dataset=dataset,
        policy_path=policy,
        top_k=3
    )

    assert report["total_queries"] == 2
    assert report["hit_rate"] == 0.5
    assert report["mrr"] == 0.5


def test_empty_dataset_rejected(policy):
    with pytest.raises(ValueError):
        evaluate_dataset(
            dataset=[],
            policy_path=policy
        )


def test_missing_relevance_labels_rejected(policy):
    with pytest.raises(ValueError):
        evaluate_query(
            query="receipts",
            relevant_headings=[],
            policy_path=policy
        )
