import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data/database/northstar.db"


def get_booking_baggage(booking_reference, database_path=None):
    if database_path is None:
        database_path = DATABASE_PATH

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    query = """
        SELECT
            bookings.booking_reference,
            bookings.flight_number,
            baggage.bag_tag,
            baggage.baggage_status
        FROM bookings
        LEFT JOIN baggage
            ON bookings.booking_reference = baggage.booking_reference
        WHERE bookings.booking_reference = ?
        ORDER BY baggage.bag_tag;
    """

    try:
        results = connection.execute(
            query, (booking_reference,)
        ).fetchall()

        # Case 1: The booking does not exist
        if not results:
            return {
                "found": False,
                "booking_reference": booking_reference,
                "bags": []
            }

        # Get the booking information from the first result
        booking = results[0]

        # Collect all bags associated with this booking
        bags = []

        for row in results:
            if row["bag_tag"] is not None:
                bags.append({
                    "bag_tag": row["bag_tag"],
                    "status": row["baggage_status"]
                })

        # Case 2: Booking exists, with or without baggage
        return {
            "found": True,
            "booking_reference": booking["booking_reference"],
            "flight_number": booking["flight_number"],
            "bags": bags
        }

    finally:
        connection.close()
