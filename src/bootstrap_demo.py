"""Initialize a local SQLite database from fictional CSV fixtures.

Run from the repository root:
    python -m src.bootstrap_demo

Existing databases are never overwritten.
"""
import csv
import sqlite3
from pathlib import Path

from src.db_schema import create_tables
from src.validate_data import (
    validate_baggage_references,
    validate_duplicate_bookings,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOKING_FIELDS = (
    "booking_reference", "passenger_id", "flight_number",
    "flight_date", "origin", "destination", "booking_status",
)
BAG_FIELDS = (
    "bag_tag", "booking_reference", "baggage_status",
    "last_known_airport", "report_id", "report_date",
)


def read_rows(path, required_fields):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(required_fields).issubset(reader.fieldnames):
            raise ValueError(f"CSV missing required columns: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV has no records: {path}")
    for row in rows:
        if any(value is None for value in row.values()):
            raise ValueError(f"Malformed CSV row: {path}")
    return rows


def bootstrap_database(project_root=PROJECT_ROOT):
    """Populate an absent database. Return True if created, False if already present."""
    root = Path(project_root)
    db_path = root / "data" / "database" / "northstar.db"

    # Never overwrite or append to a user's existing database.
    if db_path.exists():
        print(f"Existing database preserved: {db_path}")
        return False

    records_path = root / "data" / "sample_records"
    bookings_path = records_path / "bookings.csv"
    baggage_path = records_path / "baggage.csv"

    missing = [str(p) for p in (bookings_path, baggage_path) if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing demo fixture files: " + ", ".join(missing)
            + ". Commit only synthetic sample records."
        )

    bookings = read_rows(bookings_path, BOOKING_FIELDS)
    baggage = read_rows(baggage_path, BAG_FIELDS)

    errors = validate_duplicate_bookings(bookings)
    errors.extend(validate_baggage_references(bookings, baggage))

    bag_tags = [bag["bag_tag"] for bag in baggage]
    if len(bag_tags) != len(set(bag_tags)):
        errors.append("Duplicate baggage tag detected")
    if errors:
        raise ValueError("Invalid demo fixtures: " + "; ".join(errors))

    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(db_path) as connection:
            create_tables(connection)
            connection.executemany(
                "INSERT INTO bookings ("
                + ", ".join(BOOKING_FIELDS)
                + ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                [tuple(row[field] for field in BOOKING_FIELDS) for row in bookings],
            )
            connection.executemany(
                "INSERT INTO baggage ("
                + ", ".join(BAG_FIELDS)
                + ") VALUES (?, ?, ?, ?, ?, ?)",
                [
                    tuple(row[field] or None for field in BAG_FIELDS)
                    for row in baggage
                ],
            )
    except Exception:
        # Only delete a database created by this bootstrap attempt.
        db_path.unlink(missing_ok=True)
        raise

    print(
        f"Created {db_path} with {len(bookings)} bookings "
        f"and {len(baggage)} baggage records."
    )
    return True


if __name__ == "__main__":
    bootstrap_database()
