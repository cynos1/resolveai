
import csv
from pathlib import Path


# Locate the project's root directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOOKINGS_FILE = PROJECT_ROOT / "data/sample_records/bookings.csv"
BAGGAGE_FILE = PROJECT_ROOT / "data/sample_records/baggage.csv"


def load_csv(file_path):
    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def validate_duplicate_bookings(bookings):
    seen = set()
    errors = []

    for booking in bookings:
        reference = booking["booking_reference"]

        if reference in seen:
            errors.append(
                f"Duplicate booking reference: {reference}"
            )
        else:
            seen.add(reference)

    return errors

def validate_baggage_references(bookings, baggage):
    booking_references = {
        booking["booking_reference"]
        for booking in bookings
    }

    errors = []

    for bag in baggage:
        if bag["booking_reference"] not in booking_references:
            errors.append(
                f"Bag {bag['bag_tag']} references an unknown booking: "
                f"{bag['booking_reference']}"
            )

    return errors


def main():
    bookings = load_csv(BOOKINGS_FILE)
    baggage = load_csv(BAGGAGE_FILE)


    errors = validate_duplicate_bookings(bookings)
    errors.extend(validate_baggage_references(bookings, baggage))

    print(f"Loaded {len(bookings)} bookings.")
    print(f"Loaded {len(baggage)} baggage records.")

    if errors:
        print("\nValidation failed:")

        for error in errors:
            print(f"- {error}")
    else:
        print("\nValidation passed: all baggage references are valid.")


if __name__ == "__main__":
    main()

