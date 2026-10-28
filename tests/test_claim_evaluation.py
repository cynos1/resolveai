"""Regression tests for human-reviewed claim evaluation."""

from copy import deepcopy

import pytest

from src.claim_evaluation import (
    make_review_template,
    validate_review,
    score_review,
)


@pytest.fixture
def report():
    return {
        "results": [
            {
                "case": {"id": "CASE_OK"},
                "http_status": 200,
                "response": {
                    "answer": (
                        "Bag BG1001 is delayed. "
                        "The policy requires receipts."
                    ),
                    "booking_data": {
                        "booking_reference": "XYZ789",
                        "bags": [
                            {
                                "bag_tag": "BG1001",
                                "status": "delayed",
                            }
                        ],
                    },
                    "policy_evidence": [
                        {
                            "id": "P1",
                            "heading": "Essential Purchases",
                            "content": (
                                "Passengers must provide receipts "
                                "for all claimed purchases."
                            ),
                        }
                    ],
                },
            },
            {
                "case": {"id": "NOT_FOUND"},
                "http_status": 404,
                "response": {"detail": "Booking not found"},
            },
        ]
    }


@pytest.fixture
def review(report):
    review = make_review_template(report)
    case = review["cases"][0]

    case["complete"] = True
    case["status_alignment"] = "consistent"
    case["claims"] = [
        {
            "span": "Bag BG1001 is delayed",
            "label": "supported",
            "rationale": "The booking record confirms this.",
            "evidence": [
                {
                    "kind": "booking",
                    "path": "bags[0].bag_tag",
                    "value": "BG1001",
                },
                {
                    "kind": "booking",
                    "path": "bags[0].status",
                    "value": "delayed",
                },
            ],
        },
        {
            "span": "The policy requires receipts",
            "label": "supported",
            "rationale": "The retrieved policy requires receipts.",
            "evidence": [
                {
                    "kind": "policy",
                    "id": "P1",
                    "quote": (
                        "Passengers must provide receipts "
                        "for all claimed purchases."
                    ),
                }
            ],
        },
    ]

    return review


def test_template_excludes_404_responses(report):
    template = make_review_template(report)

    assert len(template["cases"]) == 1
    assert template["cases"][0]["case_id"] == "CASE_OK"
    assert template["cases"][0]["complete"] is False


def test_valid_review_passes(report, review):
    assert validate_review(report, review) is True

    result = score_review(report, review)

    assert result["status"] == "complete"
    assert result["reviewed_claims"] == 2
    assert result["claim_counts"]["supported"] == 2
    assert result["supported_claim_fraction"] == 1.0


def test_claim_must_appear_in_answer(report, review):
    review["cases"][0]["claims"][0]["span"] = (
        "The suitcase is at Gate 7"
    )

    with pytest.raises(ValueError, match="Claim span"):
        validate_review(report, review)


def test_fabricated_policy_quote_is_rejected(report, review):
    review["cases"][0]["claims"][1]["evidence"][0]["quote"] = (
        "All passengers receive $5000."
    )

    with pytest.raises(ValueError, match="Policy quote"):
        validate_review(report, review)


def test_unknown_policy_source_is_rejected(report, review):
    review["cases"][0]["claims"][1]["evidence"][0]["id"] = "P999"

    with pytest.raises(ValueError, match="Policy source"):
        validate_review(report, review)


def test_incorrect_booking_value_is_rejected(report, review):
    review["cases"][0]["claims"][0]["evidence"][1]["value"] = (
        "delivered"
    )

    with pytest.raises(ValueError, match="Booking evidence value"):
        validate_review(report, review)


def test_nonexistent_booking_path_is_rejected(report, review):
    review["cases"][0]["claims"][0]["evidence"][0]["path"] = (
        "bags[9].bag_tag"
    )

    with pytest.raises(ValueError, match="Invalid booking list index"):
        validate_review(report, review)


def test_invalid_faithfulness_label_is_rejected(report, review):
    review["cases"][0]["claims"][0]["label"] = "probably_true"

    with pytest.raises(ValueError, match="faithfulness label"):
        validate_review(report, review)


def test_completed_case_requires_claims(report, review):
    review["cases"][0]["claims"] = []

    with pytest.raises(ValueError, match="no claims"):
        validate_review(report, review)


def test_incomplete_review_is_not_scored(report, review):
    partial = deepcopy(review)
    partial["cases"][0]["complete"] = False
    partial["cases"][0]["status_alignment"] = "not_assessed"

    result = score_review(report, partial)

    assert result["status"] == "pending"
    assert result["reviewed_claims"] == 0
    assert result["supported_claim_fraction"] is None


def test_supported_claim_requires_evidence(report, review):
    review["cases"][0]["claims"][0]["evidence"] = []

    with pytest.raises(ValueError, match="require source evidence"):
        validate_review(report, review)


def test_completed_case_requires_status_review(report, review):
    review["cases"][0]["status_alignment"] = "not_assessed"

    with pytest.raises(ValueError, match="needs status alignment"):
        validate_review(report, review)
