from fastapi import FastAPI, HTTPException
from src.semantic_investigation_api import (
    router as semantic_investigation_router,
)
from src.grounded_answer_api import (
    router as grounded_answer_router,
)
from pathlib import Path
from fastapi import Query
from pydantic import BaseModel
from src.investigation_service import investigate_booking
from src.schemas import InvestigationResponse
from src.policy_retrieval import search_policy, POLICY_PATH
from src.schemas import PolicySearchResult
from fastapi import Depends
from src.database_tools import DATABASE_PATH
from src.schemas import BookingBaggageResponse
from src.database_tools import get_booking_baggage

app = FastAPI(
    title="ResolveAI API",
    description="AI-assisted airline customer support investigation system",
    version="0.1.0"
)
app.include_router(grounded_answer_router)
app.include_router(semantic_investigation_router)
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
# --------------------------------------------------
# POLICY RETRIEVAL DEPENDENCY
# --------------------------------------------------

def get_policy_path():
    return POLICY_PATH


# --------------------------------------------------
# POLICY SEARCH ENDPOINT
# --------------------------------------------------

@app.get(
    "/policies/search",
    response_model=list[PolicySearchResult]
)
def policy_search(
    query: str = Query(
        min_length=1,
        description="Question or keywords to search for"
    ),
    top_k: int = Query(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of matching sections"
    ),
    policy_path: Path = Depends(get_policy_path)
):
    return search_policy(
        query=query,
        policy_path=policy_path,
        top_k=top_k
    )
class InvestigationRequest(BaseModel):
    booking_reference: str
    question: str


@app.post(
    "/investigations",
    response_model=InvestigationResponse
)
def create_investigation(
    request: InvestigationRequest,
    database_path: Path = Depends(get_database_path),
    policy_path: Path = Depends(get_policy_path)
):
    result = investigate_booking(
        booking_reference=request.booking_reference,
        question=request.question,
        database_path=database_path,
        policy_path=policy_path
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Booking {request.booking_reference} not found"
        )

    return result
