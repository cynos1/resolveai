import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = PROJECT_ROOT / "data/database/northstar.db"
BOOKINGS_PATH = PROJECT_ROOT / "data/sample_records/bookings.csv"

connection = sqlite3.connect(DATABASE_PATH)
connection.execute("PRAGMA foreign_keys = ON;")

with open(BOOKINGS_PATH, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for booking in reader:
        connection.execute(
            """
            INSERT OR IGNORE INTO bookings (
                booking_reference,
                passenger_id,
                flight_number,
                flight_date,
                origin,
                destination,
                booking_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                booking["booking_reference"],
                booking["passenger_id"],
                booking["flight_number"],
                booking["flight_date"],
                booking["origin"],
                booking["destination"],
                booking["booking_status"]
            )
        )
BAGGAGE_PATH = PROJECT_ROOT / "data/sample_records/baggage.csv"

with open(BAGGAGE_PATH, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for bag in reader:
        connection.execute(
            """
            INSERT OR IGNORE INTO baggage (
                bag_tag,
                booking_reference,
                baggage_status,
                last_known_airport,
                report_id,
                report_date
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                bag["bag_tag"],
                bag["booking_reference"],
                bag["baggage_status"],
                bag["last_known_airport"] or None,
                bag["report_id"] or None,
                bag["report_date"] or None
            )
        )
connection.commit()
connection.close()

print("Booking records imported successfully.")
