import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.main import app, get_database_path
from src.db_schema import create_tables


# --------------------------------------------------
# TEST FIXTURE
# --------------------------------------------------

@pytest.fixture
def client(tmp_path):
    test_db = tmp_path / "northstar_test.db"

    connection = sqlite3.connect(test_db)

    try:
        create_tables(connection)

        # Booking with multiple bags
        connection.execute("""
            INSERT INTO bookings VALUES (
                'TEST123', 'P_TEST', 'NS999',
                '2026-10-15', 'BWI', 'MIA', 'completed'
            )
        """)

        # Booking without baggage
        connection.execute("""
            INSERT INTO bookings VALUES (
                'EMPTY123', 'P_EMPTY', 'NS888',
                '2026-10-16', 'BWI', 'ATL', 'completed'
            )
        """)

        connection.execute("""
            INSERT INTO baggage VALUES (
                'TESTBAG1', 'TEST123', 'delayed',
                'MIA', 'RPT_TEST', '2026-10-15'
            )
        """)

        connection.execute("""
            INSERT INTO baggage VALUES (
                'TESTBAG2', 'TEST123', 'delivered',
                'MIA', NULL, NULL
            )
        """)

        connection.commit()

    finally:
        connection.close()

    app.dependency_overrides[get_database_path] = lambda: test_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_database_path, None)


# --------------------------------------------------
# API TESTS
# --------------------------------------------------

def test_existing_booking_with_multiple_bags(client):
    response = client.get("/bookings/TEST123/baggage")

    assert response.status_code == 200

    data = response.json()

    assert data["found"] is True
    assert data["booking_reference"] == "TEST123"
    assert data["flight_number"] == "NS999"

    assert data["bags"] == [
        {"bag_tag": "TESTBAG1", "status": "delayed"},
        {"bag_tag": "TESTBAG2", "status": "delivered"}
    ]


def test_booking_without_baggage(client):
    response = client.get("/bookings/EMPTY123/baggage")

    assert response.status_code == 200

    data = response.json()

    assert data["found"] is True
    assert data["booking_reference"] == "EMPTY123"
    assert data["bags"] == []


def test_unknown_booking(client):
    response = client.get("/bookings/UNKNOWN123/baggage")

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Booking UNKNOWN123 not found"
    )


# --------------------------------------------------
# DATABASE INTEGRITY TESTS
# --------------------------------------------------

def test_invalid_foreign_key(tmp_path):
    test_db = tmp_path / "foreign_key_test.db"

    connection = sqlite3.connect(test_db)

    try:
        create_tables(connection)

        with pytest.raises(
            sqlite3.IntegrityError,
            match="FOREIGN KEY constraint failed"
        ):
            connection.execute("""
                INSERT INTO baggage (
                    bag_tag,
                    booking_reference,
                    baggage_status
                )
                VALUES (
                    'INVALID_BAG',
                    'UNKNOWN123',
                    'delayed'
                )
            """)

    finally:
        connection.close()


def test_duplicate_booking_reference(tmp_path):
    test_db = tmp_path / "duplicate_test.db"

    connection = sqlite3.connect(test_db)

    try:
        create_tables(connection)

        booking = (
            "DUP123", "P_TEST", "NS999",
            "2026-10-15", "BWI", "MIA", "completed"
        )

        connection.execute("""
            INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?)
        """, booking)

        with pytest.raises(
            sqlite3.IntegrityError,
            match="UNIQUE constraint failed"
        ):
            connection.execute("""
                INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?)
            """, booking)

    finally:
        connection.close()
