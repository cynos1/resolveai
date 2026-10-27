
from typing import Any, Callable

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.answer_generation import (
    GENERATION_MODEL,
    ABSTENTION_MESSAGE,
    generate_grounded_answer,
    prepare_evidence,
    validate_generated_answer,
)

from src.database_tools import get_booking_baggage

from src.persistent_index import (
    get_or_build_index,
    search_persistent_index,
)

from src.semantic_retrieval import embed_texts


router = APIRouter(
    prefix="/investigations",
    tags=["Grounded AI Investigations"],
)


class GroundedAnswerRequest(BaseModel):
    booking_reference: str = Field(min_length=1)
    question: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class GroundedAnswerResponse(BaseModel):
    booking_reference: str
    question: str
    answer: str
    status: str
    citations: list[str]
    policy_evidence: list[dict[str, Any]]
    booking_data: dict[str, Any]
    index_status: str
    retrieval_method: str
    generation_model: str


def get_booking_lookup():
    return get_booking_baggage


def get_index_loader():
    return get_or_build_index


def get_query_embedder():
    return embed_texts


def get_answer_generator():
    return generate_grounded_answer


@router.post(
    "/answer",
    response_model=GroundedAnswerResponse,
)
def investigate_and_answer(
    request: GroundedAnswerRequest,
    booking_lookup: Callable = Depends(get_booking_lookup),
    index_loader: Callable = Depends(get_index_loader),
    embedder: Callable = Depends(get_query_embedder),
    generator: Callable = Depends(get_answer_generator),
):
    """Investigate a booking and generate a grounded answer."""

    booking_data = booking_lookup(
        request.booking_reference
    )

    if not booking_data.get("found", False):
        raise HTTPException(
            status_code=404,
            detail="Booking reference not found",
        )

    try:
        index, index_status = index_loader()

        retrieved = search_persistent_index(
            query=request.question,
            index=index,
            top_k=request.top_k,
            embedder=embedder,
        )

        evidence = prepare_evidence(retrieved)

        if not evidence:
            validated = {
                "answer": ABSTENTION_MESSAGE,
                "citations": [],
                "abstained": True,
            }
        else:
            generated = generator(
                question=request.question,
                booking_data=booking_data,
                policy_evidence=evidence,
            )

            validated = validate_generated_answer(
                generated,
                evidence,
            )

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail="Local AI service unavailable",
        ) from exc

    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI investigation processing failed",
        ) from exc

    return GroundedAnswerResponse(
        booking_reference=request.booking_reference,
        question=request.question,
        answer=validated["answer"],
        status=(
            "insufficient_evidence"
            if validated["abstained"]
            else "answered"
        ),
        citations=validated["citations"],
        policy_evidence=evidence,
        booking_data=booking_data,
        index_status=index_status,
        retrieval_method="semantic",
        generation_model=GENERATION_MODEL,
    )

