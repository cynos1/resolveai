import pytest
from fastapi.testclient import TestClient

from src.main import app

from src.semantic_investigation_api import (
    get_booking_lookup,
    get_policy_index,
    get_query_embedder,
)

def fake_embedder(texts):
    vectors = []

    for text in texts:
        if "tracking" in text.lower() or "suitcase" in text.lower():
            vectors.append([0.0, 1.0])
        else:
            vectors.append([1.0, 0.0])

    return vectors


@pytest.fixture
def client():
    index = {
        "dimensions": 2,
        "sections": [
            {
                "heading": "Reporting",
                "content": "Report delayed baggage.",
            },
            {
                "heading": "Tracking",
                "content": "Track your suitcase status.",
            },
        ],
        "embeddings": [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
    }

    def fake_booking(booking_reference: str):
        if booking_reference == "UNKNOWN":
            return {"found": False}

        return {
            "found": True,
            "booking_reference": booking_reference,
            "baggage_status": "Delayed",
        }
    app.dependency_overrides[get_booking_lookup] = (
    lambda: fake_booking
)
    app.dependency_overrides[get_policy_index] = lambda: (
        index,
        "reused",
    )
    app.dependency_overrides[get_query_embedder] = (
        lambda: fake_embedder
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_semantic_investigation(client):
    response = client.post(
        "/investigations/semantic",
        json={
            "booking_reference": "NS1001",
            "question": "Where is my suitcase?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["booking_reference"] == "NS1001"
    assert data["retrieval_method"] == "semantic"
    assert data["index_status"] == "reused"

    assert (
        data["policy_evidence"][0]["heading"]
        == "Tracking"
    )


def test_unknown_booking(client):
    response = client.post(
        "/investigations/semantic",
        json={
            "booking_reference": "UNKNOWN",
            "question": "Where is my suitcase?",
        },
    )

    assert response.status_code == 404


def test_missing_question(client):
    response = client.post(
        "/investigations/semantic",
        json={
            "booking_reference": "NS1001",
        },
    )

    assert response.status_code == 422


def test_invalid_top_k(client):
    response = client.post(
        "/investigations/semantic",
        json={
            "booking_reference": "NS1001",
            "question": "Where is my suitcase?",
            "top_k": 0,
        },
    )

    assert response.status_code == 422


def test_top_k_one(client):
    response = client.post(
        "/investigations/semantic",
        json={
            "booking_reference": "NS1001",
            "question": "Where is my suitcase?",
            "top_k": 1,
        },
    )

    assert response.status_code == 200

    evidence = response.json()["policy_evidence"]

    assert len(evidence) == 1
    assert evidence[0]["heading"] == "Tracking"
