from pydantic import BaseModel


class BagResponse(BaseModel):
    bag_tag: str
    status: str


class BookingBaggageResponse(BaseModel):
    found: bool
    booking_reference: str
    flight_number: str
    bags: list[BagResponse]
class PolicySearchResult(BaseModel):
    heading: str
    content: str
    score: int
class InvestigationResponse(BaseModel):
    booking_reference: str
    question: str
    booking: BookingBaggageResponse
    policy_evidence: list[PolicySearchResult]
