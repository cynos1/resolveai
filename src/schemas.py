from pydantic import BaseModel


class BagResponse(BaseModel):
    bag_tag: str
    status: str


class BookingBaggageResponse(BaseModel):
    found: bool
    booking_reference: str
    flight_number: str
    bags: list[BagResponse]
