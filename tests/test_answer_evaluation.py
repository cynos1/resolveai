"""Offline unit tests for deterministic answer-evaluation checks."""
from src.answer_evaluation import evaluate_response, summarize_results


def sample_case(**changes):
    case = {
        "id": "CASE1",
        "category": "policy_grounding",
        "expected_http_status": 200,
        "expected_abstention": False,
        "require_policy_citation": True,
    }
    case.update(changes)
    return case


def sample_response(**changes):
    response = {
        "answer": "The policy requires a report.",
        "status": "answered",
        "citations": ["P1"],
        "policy_evidence": [
            {"id": "P1", "heading": "Reporting", "content": "Report baggage."}
        ],
        "booking_data": {"found": True, "bags": []},
    }
    response.update(changes)
    return response


def test_valid_structure_passes():
    assert evaluate_response(sample_case(), 200, sample_response())["passed"]


def test_unknown_citation_fails():
    evaluation = evaluate_response(
        sample_case(), 200, sample_response(citations=["P999"])
    )
    assert not evaluation["passed"]
    assert not evaluation["checks"]["citations_known"]


def test_duplicate_citation_fails():
    evaluation = evaluate_response(
        sample_case(), 200, sample_response(citations=["P1", "P1"])
    )
    assert not evaluation["checks"]["citations_unique"]


def test_expected_abstention_passes():
    evaluation = evaluate_response(
        sample_case(expected_abstention=True, require_policy_citation=False),
        200,
        sample_response(
            answer="No verified GPS coordinates are available.",
            citations=[],
            status="insufficient_evidence",
        ),
    )
    assert evaluation["passed"]


def test_missing_expected_abstention_fails():
    evaluation = evaluate_response(
        sample_case(expected_abstention=True, require_policy_citation=False),
        200,
        sample_response(),
    )
    assert not evaluation["checks"]["abstention"]


def test_missing_required_citation_fails():
    evaluation = evaluate_response(
        sample_case(),
        200,
        sample_response(citations=[]),
    )
    assert not evaluation["checks"]["policy_citation_present"]


def test_expected_missing_booking_status_passes():
    evaluation = evaluate_response(
        sample_case(expected_http_status=404),
        404,
        {"detail": "Booking reference not found"},
    )
    assert evaluation["passed"]


def test_missing_response_structure_fails():
    evaluation = evaluate_response(sample_case(), 503, {"detail": "error"})
    assert not evaluation["passed"]
    assert not evaluation["checks"]["http_status"]


def test_manual_review_is_separate_from_deterministic_pass():
    evaluation = evaluate_response(
        sample_case(
            review_focus="Check whether the claim is true.",
        ),
        200,
        sample_response(),
    )
    assert evaluation["manual_review_required"] is True
    assert evaluation["review_focus"].startswith("Check")


def test_summary_uses_applicable_checks_only():
    results = [
        {"evaluation": {
            "passed": True,
            "manual_review_required": True,
            "checks": {"http_status": True, "citations_known": True},
        }},
        {"evaluation": {
            "passed": False,
            "manual_review_required": False,
            "checks": {"http_status": False},
        }},
    ]
    summary = summarize_results(results)
    assert summary["total_cases"] == 2
    assert summary["passed_cases"] == 1
    assert summary["pass_rate"] == 0.5
    assert summary["manual_review_cases"] == 1
    assert summary["check_pass_rates"]["http_status"] == 0.5
    assert summary["check_pass_rates"]["citations_known"] == 1.0


def test_empty_summary():
    assert summarize_results([])["total_cases"] == 0
