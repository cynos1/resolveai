from fastapi import FastAPI, HTTPException
from fastapi import Depends
from src.database_tools import DATABASE_PATH
from src.schemas import BookingBaggageResponse
from src.database_tools import get_booking_baggage

app = FastAPI(
    title="ResolveAI API",
    description="AI-assisted airline customer support investigation system",
    version="0.1.0"
)
def get_database_path():
    return DATABASE_PATH

@app.get("/")
def home():
    return {
        "message": "Welcome to ResolveAI"
    }


@app.get(
    "/bookings/{booking_reference}/baggage",
    response_model=BookingBaggageResponse
)
def booking_baggage(
    booking_reference: str,
    database_path: str = Depends(get_database_path)
):
    result = get_booking_baggage(booking_reference,database_path=database_path)

    if not result["found"]:
        raise HTTPException(
            status_code=404,
            detail=f"Booking {booking_reference} not found"
        )

    return result
