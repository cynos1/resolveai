import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.main import (
    app,
    get_database_path,
    get_policy_path
)
from src.db_schema import create_tables


@pytest.fixture
def client(tmp_path):
    test_db = tmp_path / "investigation_test.db"
    test_policy = tmp_path / "investigation_policy.md"

    connection = sqlite3.connect(test_db)

    try:
        create_tables(connection)

        connection.execute("""
            INSERT INTO bookings VALUES (
                'TEST123', 'P001', 'NS999',
                '2026-10-15', 'BWI', 'MIA', 'completed'
            )
        """)

        connection.execute("""
            INSERT INTO bookings VALUES (
                'EMPTY123', 'P002', 'NS888',
                '2026-10-16', 'BWI', 'ATL', 'completed'
            )
        """)

        connection.execute("""
            INSERT INTO baggage VALUES (
                'BAG001', 'TEST123', 'delayed',
                'MIA', 'RPT001', '2026-10-15'
            )
        """)

        connection.commit()

    finally:
        connection.close()

    test_policy.write_text(
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

    app.dependency_overrides[get_database_path] = lambda: test_db
    app.dependency_overrides[get_policy_path] = lambda: test_policy

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_database_path, None)
        app.dependency_overrides.pop(get_policy_path, None)


def test_investigation_returns_combined_evidence(client):
    response = client.post(
        "/investigations",
        json={
            "booking_reference": "TEST123",
            "question": "reimbursement receipts"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["booking_reference"] == "TEST123"
    assert data["question"] == "reimbursement receipts"

    assert data["booking"]["found"] is True
    assert data["booking"]["bags"] == [
        {"bag_tag": "BAG001", "status": "delayed"}
    ]

    assert data["policy_evidence"]
    assert data["policy_evidence"][0]["heading"] == "Reimbursement"


def test_investigation_unknown_booking(client):
    response = client.post(
        "/investigations",
        json={
            "booking_reference": "UNKNOWN123",
            "question": "reimbursement"
        }
    )

    assert response.status_code == 404


def test_investigation_booking_without_baggage(client):
    response = client.post(
        "/investigations",
        json={
            "booking_reference": "EMPTY123",
            "question": "delayed baggage"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["booking"]["found"] is True
    assert data["booking"]["bags"] == []


def test_investigation_no_policy_match(client):
    response = client.post(
        "/investigations",
        json={
            "booking_reference": "TEST123",
            "question": "volcano submarine"
        }
    )

    assert response.status_code == 200
    assert response.json()["policy_evidence"] == []


def test_investigation_missing_question(client):
    response = client.post(
        "/investigations",
        json={
            "booking_reference": "TEST123"
        }
    )

    assert response.status_code == 422
