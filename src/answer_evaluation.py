"""Deterministic checks for ResolveAI answer-evaluation runs.

Structural validity is NOT a test of factual faithfulness or citation support.
"""


def evaluate_response(case, http_status, response):
    """Check the API contract and case-specific observable expectations."""
    checks = {
        "http_status": http_status == case["expected_http_status"],
    }

    if case["expected_http_status"] != 200:
        return _result(case, checks)

    if http_status != 200 or not isinstance(response, dict):
        checks["response_structure"] = False
        return _result(case, checks)

    required = {
        "answer",
        "status",
        "citations",
        "policy_evidence",
        "booking_data",
    }
    valid_shape = (
        required.issubset(response)
        and isinstance(response.get("answer"), str)
        and bool(response.get("answer", "").strip())
        and isinstance(response.get("status"), str)
        and isinstance(response.get("citations"), list)
        and isinstance(response.get("policy_evidence"), list)
        and isinstance(response.get("booking_data"), dict)
    )
    checks["response_structure"] = valid_shape

    if not valid_shape:
        return _result(case, checks)

    citations = response["citations"]
    evidence = response["policy_evidence"]

    evidence_well_formed = all(
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("heading"), str)
        and isinstance(item.get("content"), str)
        for item in evidence
    )
    checks["evidence_structure"] = evidence_well_formed

    valid_ids = {
        item["id"]
        for item in evidence
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
    }
    citations_are_strings = all(
        isinstance(citation, str)
        for citation in citations
    )
    checks["citations_known"] = (
        citations_are_strings
        and all(citation in valid_ids for citation in citations)
    )
    checks["citations_unique"] = (
        citations_are_strings
        and len(citations) == len(set(citations))
    )
    checks["status_valid"] = response["status"] in {
        "answered", "insufficient_evidence"
    }

    if "expected_abstention" in case:
        checks["abstention"] = (
            (response["status"] == "insufficient_evidence")
            == case["expected_abstention"]
        )

    if case.get("require_policy_citation", False):
        checks["policy_citation_present"] = len(citations) > 0

    return _result(case, checks)


def _result(case, checks):
    """Keep manual-review requirements visible, not buried in a pass rate."""
    return {
        "case_id": case["id"],
        "category": case["category"],
        "checks": checks,
        "passed": all(checks.values()),
        "manual_review_required": bool(case.get("review_focus")),
        "review_focus": case.get("review_focus", ""),
    }


def summarize_results(results):
    """Summarize only deterministic checks; manual cases remain unscored."""
    count = len(results)
    if count == 0:
        return {
            "total_cases": 0,
            "passed_cases": 0,
            "pass_rate": 0.0,
            "manual_review_cases": 0,
            "check_pass_rates": {},
        }

    evaluations = [item["evaluation"] for item in results]
    passed_cases = sum(item["passed"] for item in evaluations)
    names = sorted({
        name
        for item in evaluations
        for name in item["checks"]
    })
    rates = {}
    for name in names:
        applicable = [
            item["checks"][name]
            for item in evaluations
            if name in item["checks"]
        ]
        rates[name] = round(sum(applicable) / len(applicable), 3)

    return {
        "total_cases": count,
        "passed_cases": passed_cases,
        "pass_rate": round(passed_cases / count, 3),
        "manual_review_cases": sum(
            item["manual_review_required"]
            for item in evaluations
        ),
        "check_pass_rates": rates,
    }
