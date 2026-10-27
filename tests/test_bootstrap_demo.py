"""Offline tests for the non-destructive demo database bootstrap."""
import csv
import sqlite3

import pytest

from src.bootstrap_demo import bootstrap_database


BOOKING_HEADER = [
    "booking_reference", "passenger_id", "flight_number",
    "flight_date", "origin", "destination", "booking_status",
]
BAG_HEADER = [
    "bag_tag", "booking_reference", "baggage_status",
    "last_known_airport", "report_id", "report_date",
]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def demo_records(root, bag_booking="XYZ789"):
    samples = root / "data" / "sample_records"
    write_csv(
        samples / "bookings.csv",
        BOOKING_HEADER,
        [["XYZ789", "P001", "NS204", "2026-10-12", "BWI", "ORD", "completed"]],
    )
    write_csv(
        samples / "baggage.csv",
        BAG_HEADER,
        [["BG001", bag_booking, "delayed", "ORD", "REP001", "2026-10-12"]],
    )


def test_bootstrap_creates_database(tmp_path):
    demo_records(tmp_path)
    assert bootstrap_database(tmp_path) is True
    database = tmp_path / "data" / "database" / "northstar.db"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM baggage").fetchone()[0] == 1


def test_bootstrap_preserves_existing_database(tmp_path):
    database = tmp_path / "data" / "database" / "northstar.db"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"existing data: do not change")
    assert bootstrap_database(tmp_path) is False
    assert database.read_bytes() == b"existing data: do not change"


def test_bootstrap_rejects_missing_fixtures(tmp_path):
    with pytest.raises(FileNotFoundError):
        bootstrap_database(tmp_path)
    assert not (tmp_path / "data" / "database" / "northstar.db").exists()


def test_bootstrap_rejects_bad_foreign_key(tmp_path):
    demo_records(tmp_path, bag_booking="NOT_FOUND")
    with pytest.raises(ValueError, match="unknown booking"):
        bootstrap_database(tmp_path)
    assert not (tmp_path / "data" / "database" / "northstar.db").exists()
