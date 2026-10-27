
from typing import Any, Callable

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.database_tools import get_booking_baggage
from src.persistent_index import (
    get_or_build_index,
    search_persistent_index,
)
from src.semantic_retrieval import embed_texts


router = APIRouter(
    prefix="/investigations",
    tags=["Semantic Investigations"],
)


class SemanticInvestigationRequest(BaseModel):
    booking_reference: str = Field(min_length=1)
    question: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class PolicyEvidence(BaseModel):
    heading: str
    content: str
    score: float


class SemanticInvestigationResponse(BaseModel):
    booking_reference: str
    question: str
    booking_data: dict[str, Any]
    policy_evidence: list[PolicyEvidence]
    index_status: str
    retrieval_method: str


def get_booking_lookup():
    """Provide the booking lookup function."""
    return get_booking_baggage


def get_policy_index():
    """Load or rebuild the persistent policy index."""
    return get_or_build_index()


def get_query_embedder():
    """Provide the query embedding function."""
    return embed_texts


@router.post(
    "/semantic",
    response_model=SemanticInvestigationResponse,
)
def investigate_semantically(
    request: SemanticInvestigationRequest,
    booking_lookup: Callable = Depends(get_booking_lookup),
    index_result: tuple = Depends(get_policy_index),
    embedder: Callable = Depends(get_query_embedder),
):
    """
    Combine database evidence and semantic policy retrieval.
    """

    booking_data = booking_lookup(request.booking_reference)

    if not booking_data.get("found", False):
        raise HTTPException(
            status_code=404,
            detail="Booking reference not found",
        )

    index, status = index_result

    try:
        evidence = search_persistent_index(
            query=request.question,
            index=index,
            top_k=request.top_k,
            embedder=embedder,
        )

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Semantic retrieval configuration error",
        ) from exc

    return SemanticInvestigationResponse(
        booking_reference=request.booking_reference,
        question=request.question,
        booking_data=booking_data,
        policy_evidence=evidence,
        index_status=status,
        retrieval_method="semantic",
    )

