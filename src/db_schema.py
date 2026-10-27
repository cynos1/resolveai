def create_tables(connection):
    connection.execute("PRAGMA foreign_keys = ON")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_reference TEXT PRIMARY KEY NOT NULL,
            passenger_id TEXT NOT NULL,
            flight_number TEXT NOT NULL,
            flight_date TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            booking_status TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS baggage (
            bag_tag TEXT PRIMARY KEY NOT NULL,
            booking_reference TEXT NOT NULL,
            baggage_status TEXT NOT NULL,
            last_known_airport TEXT,
            report_id TEXT,
            report_date TEXT,
            FOREIGN KEY (booking_reference)
                REFERENCES bookings(booking_reference)
        )
    """)
