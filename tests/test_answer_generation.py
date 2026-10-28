"""Offline tests for the structured local LLM integration.

These tests verify contracts and prompt wiring, not factual truth or whether
the real model will follow the instructions.
"""
import json

import pytest

from src.answer_generation import (
    SYSTEM_PROMPT,
    build_user_prompt,
    generate_grounded_answer,
    prepare_evidence,
    validate_generated_answer,
)


def example_evidence():
    return [{"id": "P1", "heading": "Tracking", "content": "No live coordinates."}]


def test_evidence_identifiers_are_assigned():
    sections = [
        {"heading": "Reporting", "content": "Report baggage."},
        {"heading": "Tracking", "content": "Tracking records are required."},
    ]
    assert [item["id"] for item in prepare_evidence(sections)] == ["P1", "P2"]


def test_user_prompt_contains_structured_source_data():
    prompt = build_user_prompt(
        "Where is my bag?",
        {"found": True, "bags": [{"bag_tag": "B1", "status": "delayed"}]},
        example_evidence(),
    )
    data = json.loads(prompt.split("\n\n", 1)[1])
    assert data["customer_question"] == "Where is my bag?"
    assert data["booking_records"]["bags"][0]["bag_tag"] == "B1"
    assert data["policy_evidence"][0]["id"] == "P1"


def test_generation_passes_grounding_instructions_to_local_model(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": json.dumps({
                "answer": "Cannot verify exact location.",
                "citations": ["P1"],
                "abstained": True,
            })}}

    def fake_post(url, json, timeout):
        captured.update({"url": url, "payload": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("src.answer_generation.requests.post", fake_post)

    result = generate_grounded_answer(
        question="What are the exact GPS coordinates?",
        booking_data={"found": True},
        policy_evidence=example_evidence(),
    )
    assert result["abstained"] is True
    assert captured["payload"]["format"] == "json"
    assert captured["payload"]["think"] is False
    assert "Set abstained=true" in captured["payload"]["messages"][0]["content"]
    assert "NEVER state" in captured["payload"]["messages"][0]["content"]


def test_structured_abstention_can_cite_explanatory_policy():
    result = validate_generated_answer(
        {"answer": "Cannot verify exact location.", "citations": ["P1"], "abstained": True},
        example_evidence(),
    )
    assert result["abstained"]
    assert result["citations"] == ["P1"]


def test_unknown_citation_is_rejected():
    with pytest.raises(ValueError, match="unknown policy source"):
        validate_generated_answer(
            {"answer": "Unknown", "citations": ["P999"], "abstained": True},
            example_evidence(),
        )


def test_duplicate_citation_is_rejected():
    with pytest.raises(ValueError, match="Duplicate citations"):
        validate_generated_answer(
            {"answer": "Unknown", "citations": ["P1", "P1"], "abstained": True},
            example_evidence(),
        )


def test_invalid_abstention_type_is_rejected():
    with pytest.raises(ValueError, match="abstention"):
        validate_generated_answer(
            {"answer": "Unknown", "citations": [], "abstained": "true"},
            example_evidence(),
        )
