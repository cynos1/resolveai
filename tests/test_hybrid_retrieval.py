import pytest

from src.hybrid_retrieval import (
    load_retrievable_sections,
    keyword_rank,
    reciprocal_rank_fusion,
    hybrid_search,
)


@pytest.fixture
def sections():
    return [
        {
            "heading": "Reporting",
            "content": "Report delayed baggage",
        },
        {
            "heading": "Reimbursement",
            "content": "Essential purchases and receipts",
        },
        {
            "heading": "Tracking",
            "content": "Baggage tracking information",
        },
    ]


def test_document_title_is_excluded(tmp_path):
    policy = tmp_path / "policy.md"

    policy.write_text(
        "# Northstar Air Policy\n"
        "\n"
        "## Reporting\n"
        "Report delayed baggage.\n"
        "\n"
        "## Tracking\n"
        "Track baggage status.\n",
        encoding="utf-8",
    )

    sections = load_retrievable_sections(policy)

    headings = [item["heading"] for item in sections]

    assert headings == ["Reporting", "Tracking"]


def test_keyword_ranking(sections):
    results = keyword_rank(
        "essential receipts",
        sections,
    )

    assert results[0]["heading"] == "Reimbursement"
    assert results[0]["score"] == 2


def test_keyword_no_match(sections):
    results = keyword_rank(
        "volcano submarine",
        sections,
    )

    assert results == []


def test_rrf_rewards_multiple_rankings():
    keyword = [
        {"heading": "A", "content": "A"},
        {"heading": "B", "content": "B"},
    ]

    semantic = [
        {"heading": "B", "content": "B"},
        {"heading": "C", "content": "C"},
    ]

    results = reciprocal_rank_fusion(
        [keyword, semantic],
        top_k=3,
    )

    assert results[0]["heading"] == "B"


def test_rrf_respects_top_k():
    ranking = [
        {"heading": "A", "content": "A"},
        {"heading": "B", "content": "B"},
    ]

    results = reciprocal_rank_fusion(
        [ranking],
        top_k=1,
    )

    assert len(results) == 1


def test_rrf_invalid_top_k():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            [],
            top_k=0,
        )


def test_hybrid_empty_query(sections):
    results = hybrid_search(
        "",
        sections,
        section_embeddings=[],
    )

    assert results == []


def test_hybrid_invalid_top_k(sections):
    with pytest.raises(ValueError):
        hybrid_search(
            "baggage",
            sections,
            section_embeddings=[],
            top_k=0,
        )
