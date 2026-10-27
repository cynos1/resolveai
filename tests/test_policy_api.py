import pytest
from fastapi.testclient import TestClient

from src.main import app, get_policy_path


@pytest.fixture
def client(tmp_path):
    policy_path = tmp_path / "test_policy.md"

    policy_path.write_text(
        "# Northstar Air Policy\n"
        "\n"
        "## Reporting\n"
        "Delayed baggage must be reported within 24 hours.\n"
        "\n"
        "## Reimbursement\n"
        "Essential purchases may be reimbursed up to $150.\n"
        "Receipts are required for reimbursement.\n"
        "\n"
        "## Human Approval\n"
        "A human agent must approve reimbursement requests.\n",
        encoding="utf-8"
    )

    app.dependency_overrides[get_policy_path] = (
        lambda: policy_path
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_policy_path, None)


def test_policy_search_returns_relevant_sections(client):
    response = client.get(
        "/policies/search",
        params={
            "query": "receipts reimbursement",
            "top_k": 2
        }
    )

    assert response.status_code == 200

    results = response.json()

    assert len(results) <= 2
    assert results[0]["heading"] == "Reimbursement"
    assert results[0]["score"] == 2
    assert "Receipts are required" in results[0]["content"]


def test_policy_search_no_match(client):
    response = client.get(
        "/policies/search",
        params={"query": "volcano submarine"}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_policy_search_rejects_empty_query(client):
    response = client.get(
        "/policies/search",
        params={"query": ""}
    )

    assert response.status_code == 422


def test_policy_search_rejects_invalid_top_k(client):
    response = client.get(
        "/policies/search",
        params={
            "query": "baggage",
            "top_k": 0
        }
    )

    assert response.status_code == 422


def test_policy_search_respects_top_k(client):
    response = client.get(
        "/policies/search",
        params={
            "query": "reimbursement",
            "top_k": 1
        }
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
