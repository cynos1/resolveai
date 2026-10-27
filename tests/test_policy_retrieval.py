import pytest

from src.policy_retrieval import (
    load_policy,
    split_into_sections,
    tokenize,
    search_policy,
)


@pytest.fixture
def sample_policy(tmp_path):
    path = tmp_path / "sample_policy.md"

    path.write_text(
        "# Delayed Baggage Policy\n"
        "\n"
        "## Reporting\n"
        "Passengers must report delayed baggage within 24 hours.\n"
        "\n"
        "## Reimbursement\n"
        "Essential purchases may be reimbursed up to $150.\n"
        "Receipts are required.\n"
        "\n"
        "## Approval\n"
        "A human agent must approve reimbursement.\n",
        encoding="utf-8",
    )

    return path


def test_load_policy(sample_policy):
    document = load_policy(sample_policy)

    assert "Delayed Baggage Policy" in document
    assert "Receipts are required" in document


def test_split_into_sections(sample_policy):
    document = load_policy(sample_policy)

    sections = split_into_sections(document)

    assert len(sections) == 3

    assert sections[0]["heading"] == "Reporting"
    assert sections[1]["heading"] == "Reimbursement"
    assert sections[2]["heading"] == "Approval"


def test_tokenize():
    terms = tokenize("Delayed BAGGAGE, within 24 hours!")

    assert terms == {
        "delayed",
        "baggage",
        "within",
        "24",
        "hours",
    }


def test_reimbursement_search(sample_policy):
    results = search_policy(
        "reimbursement receipts",
        policy_path=sample_policy,
    )

    assert results
    assert results[0]["heading"] == "Reimbursement"
    assert results[0]["score"] == 2


def test_no_matching_terms(sample_policy):
    results = search_policy(
        "volcano submarine",
        policy_path=sample_policy,
    )

    assert results == []


def test_empty_query(sample_policy):
    results = search_policy(
        "",
        policy_path=sample_policy,
    )

    assert results == []


def test_invalid_top_k(sample_policy):
    with pytest.raises(ValueError, match="top_k"):
        search_policy(
            "baggage",
            policy_path=sample_policy,
            top_k=0,
        )
