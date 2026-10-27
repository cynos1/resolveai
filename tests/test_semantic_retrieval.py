import pytest

from src.semantic_retrieval import (
    cosine_similarity,
    rank_sections,
    semantic_search,
)


def test_identical_vectors():
    score = cosine_similarity(
        [1, 2, 3],
        [1, 2, 3]
    )

    assert score == pytest.approx(1.0)


def test_orthogonal_vectors():
    score = cosine_similarity(
        [1, 0],
        [0, 1]
    )

    assert score == pytest.approx(0.0)


def test_opposite_vectors():
    score = cosine_similarity(
        [1, 0],
        [-1, 0]
    )

    assert score == pytest.approx(-1.0)


def test_mismatched_dimensions():
    with pytest.raises(ValueError):
        cosine_similarity(
            [1, 2],
            [1, 2, 3]
        )


def test_zero_vector():
    with pytest.raises(ValueError):
        cosine_similarity(
            [0, 0],
            [1, 2]
        )


def test_rank_sections():
    sections = [
        {
            "heading": "Reporting",
            "content": "Report baggage"
        },
        {
            "heading": "Reimbursement",
            "content": "Essential purchases"
        }
    ]

    embeddings = [
        [1, 0],
        [0, 1]
    ]

    results = rank_sections(
        query_embedding=[0, 1],
        sections=sections,
        section_embeddings=embeddings,
        top_k=1
    )

    assert len(results) == 1
    assert results[0]["heading"] == "Reimbursement"
    assert results[0]["score"] == pytest.approx(1.0)


def test_empty_query_does_not_call_ollama():
    results = semantic_search(
        query="",
        sections=[],
        section_embeddings=[]
    )

    assert results == []


def test_invalid_top_k():
    with pytest.raises(ValueError):
        rank_sections(
            query_embedding=[1, 0],
            sections=[],
            section_embeddings=[],
            top_k=0
        )
