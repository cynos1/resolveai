import sqlite3
from pathlib import Path

from src.db_schema import create_tables

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data/database/northstar.db"


def main():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        create_tables(connection)
        connection.commit()
        print("Database tables created or already exist.")

    finally:
        connection.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
