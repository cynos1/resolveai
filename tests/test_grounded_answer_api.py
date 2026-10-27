
import pytest
from fastapi.testclient import TestClient

from src.main import app

from src.grounded_answer_api import (
    get_booking_lookup,
    get_index_loader,
    get_query_embedder,
    get_answer_generator,
)


def fake_embedder(texts):
    return [[0.0, 1.0] for _ in texts]


def fake_generator(question, booking_data, policy_evidence):
    return {
        "answer": (
            "The policy explains how baggage tracking works."
        ),
        "citations": ["P1"],
        "abstained": False,
    }


@pytest.fixture
def client():
    index = {
        "dimensions": 2,
        "sections": [
            {
                "heading": "Baggage Tracking",
                "content": "Customers can request tracking updates.",
            },
        ],
        "embeddings": [
            [0.0, 1.0],
        ],
    }

    def fake_booking(reference):
        if reference == "UNKNOWN":
            return {"found": False}

        return {
            "found": True,
            "booking_reference": reference,
            "baggage_status": "Delayed",
        }

    app.dependency_overrides[get_booking_lookup] = (
        lambda: fake_booking
    )

    app.dependency_overrides[get_index_loader] = (
        lambda: lambda: (index, "reused")
    )

    app.dependency_overrides[get_query_embedder] = (
        lambda: fake_embedder
    )

    app.dependency_overrides[get_answer_generator] = (
        lambda: fake_generator
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_grounded_answer(client):
    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
            "question": "How does baggage tracking work?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "answered"
    assert data["citations"] == ["P1"]
    assert data["retrieval_method"] == "semantic"
    assert data["index_status"] == "reused"


def test_unknown_booking(client):
    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "UNKNOWN",
            "question": "Where is my suitcase?",
        },
    )

    assert response.status_code == 404


def test_missing_question(client):
    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
        },
    )

    assert response.status_code == 422


def test_invalid_top_k(client):
    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
            "question": "Where is my suitcase?",
            "top_k": 0,
        },
    )

    assert response.status_code == 422


def test_invalid_citation_rejected(client):
    def bad_generator(question, booking_data, policy_evidence):
        return {
            "answer": "Your suitcase is in Paris.",
            "citations": ["P999"],
            "abstained": False,
        }

    app.dependency_overrides[get_answer_generator] = (
        lambda: bad_generator
    )

    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
            "question": "Where is my suitcase?",
        },
    )

    assert response.status_code == 503


def test_model_can_abstain(client):
    def abstaining_generator(
        question,
        booking_data,
        policy_evidence,
    ):
        return {
            "answer": (
                "The available records do not establish "
                "the suitcase's exact location."
            ),
            "citations": [],
            "abstained": True,
        }

    app.dependency_overrides[get_answer_generator] = (
        lambda: abstaining_generator
    )

    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
            "question": "Where exactly is my suitcase?",
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["status"]
        == "insufficient_evidence"
    )


def test_invalid_model_output_rejected(client):
    app.dependency_overrides[get_answer_generator] = (
        lambda: lambda **kwargs: {
            "answer": "",
            "citations": [],
            "abstained": False,
        }
    )

    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
            "question": "Where is my suitcase?",
        },
    )

    assert response.status_code == 503


def test_missing_evidence_abstains_without_llm(client):
    empty_index = {
        "dimensions": 2,
        "sections": [],
        "embeddings": [],
    }

    app.dependency_overrides[get_index_loader] = (
        lambda: lambda: (empty_index, "reused")
    )

    def should_not_generate(**kwargs):
        raise AssertionError("LLM should not be called")

    app.dependency_overrides[get_answer_generator] = (
        lambda: should_not_generate
    )

    response = client.post(
        "/investigations/answer",
        json={
            "booking_reference": "NS1001",
            "question": "What does the policy say?",
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["status"]
        == "insufficient_evidence"
    )

