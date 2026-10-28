"""Human-audited claim-level faithfulness evaluation for ResolveAI.

This module validates evidence pointers and aggregates *reviewer-assigned*
labels. It does NOT automatically establish that a claim is true.
"""
import re
from collections import Counter


LABELS = frozenset({"supported", "contradicted", "unverifiable"})
PATH_PART = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?$")


def make_review_template(report):
    """Prepare an empty, explicitly incomplete human-review worksheet."""
    cases = []
    for item in report["results"]:
        if item.get("http_status") != 200:
            continue
        answer = item.get("response", {}).get("answer")
        if not isinstance(answer, str) or not answer.strip():
            continue
        cases.append({
            "case_id": item["case"]["id"],
            "complete": False,
            "status_alignment": "not_assessed",
            "claims": [],
            "review_notes": "",
        })
    return {
        "reviewer": "human",
        "annotation_version": 1,
        "cases": cases,
    }


def resolve_booking_path(booking_data, path):
    """Read a dot-and-list-index path from the exact supplied booking evidence."""
    if not isinstance(path, str) or not path:
        raise ValueError("Booking evidence path must be a nonempty string")
    value = booking_data
    for component in path.split("."):
        matched = PATH_PART.fullmatch(component)
        if not matched or not isinstance(value, dict):
            raise ValueError(f"Invalid booking evidence path: {path}")
        key, index = matched.groups()
        if key not in value:
            raise ValueError(f"Unknown booking evidence path: {path}")
        value = value[key]
        if index is not None:
            if not isinstance(value, list) or int(index) >= len(value):
                raise ValueError(f"Invalid booking list index in: {path}")
            value = value[int(index)]
    return value


def _validate_evidence(evidence, response):
    if not isinstance(evidence, list):
        raise ValueError("Claim evidence must be a list")
    sections = {
        item["id"]: item
        for item in response.get("policy_evidence", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for entry in evidence:
        if not isinstance(entry, dict):
            raise ValueError("Evidence entries must be objects")
        if entry.get("kind") == "policy":
            section = sections.get(entry.get("id"))
            if section is None:
                raise ValueError(f"Policy source does not exist: {entry.get('id')}")
            quote = entry.get("quote")
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError("Policy evidence requires a nonempty quote")
            if quote.strip() not in section.get("content", ""):
                raise ValueError("Policy quote is not in the retrieved section")
        elif entry.get("kind") == "booking":
            if "value" not in entry:
                raise ValueError("Booking evidence must include the observed value")
            actual = resolve_booking_path(
                response.get("booking_data", {}),
                entry.get("path"),
            )
            if actual != entry["value"] or type(actual) is not type(entry["value"]):
                raise ValueError("Booking evidence value differs from retrieved data")
        else:
            raise ValueError("Evidence kind must be 'policy' or 'booking'")


def validate_review(report, review):
    """Reject incorrect references and malformed or duplicate annotations."""
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError("Invalid evaluation report")
    if not isinstance(review, dict) or not isinstance(review.get("cases"), list):
        raise ValueError("Invalid claim review")
    if review.get("reviewer") != "human" or review.get("annotation_version") != 1:
        raise ValueError("Review must identify human annotation version 1")

    sources = {}
    for item in report["results"]:
        case_id = item["case"]["id"]
        if case_id in sources:
            raise ValueError(f"Duplicate report case: {case_id}")
        if item.get("http_status") == 200 and isinstance(item.get("response"), dict):
            sources[case_id] = item["response"]

    expected = {
        key for key, value in sources.items()
        if isinstance(value.get("answer"), str) and value["answer"].strip()
    }
    found = set()
    for case_review in review["cases"]:
        if not isinstance(case_review, dict):
            raise ValueError("Review cases must be objects")
        case_id = case_review.get("case_id")
        if case_id not in expected or case_id in found:
            raise ValueError(f"Unknown or duplicated review case: {case_id}")
        found.add(case_id)
        if not isinstance(case_review.get("complete"), bool):
            raise ValueError(f"Invalid completion flag: {case_id}")
        if case_review.get("status_alignment") not in {
            "consistent", "inconsistent", "not_assessed"
        }:
            raise ValueError(f"Invalid status alignment label: {case_id}")

        claims = case_review.get("claims")
        if not isinstance(claims, list):
            raise ValueError(f"Claims must be a list: {case_id}")
        if case_review["complete"] and not claims:
            raise ValueError(f"Completed review has no claims: {case_id}")
        if case_review["complete"] and case_review["status_alignment"] == "not_assessed":
            raise ValueError(f"Completed review needs status alignment: {case_id}")
        seen_spans = set()
        for claim in claims:
            if not isinstance(claim, dict):
                raise ValueError("Claims must be objects")
            span = claim.get("span")
            if not isinstance(span, str) or not span.strip():
                raise ValueError("Every claim requires an exact nonempty answer span")
            if span not in sources[case_id]["answer"]:
                raise ValueError("Claim span does not occur in the model answer")
            if span in seen_spans:
                raise ValueError("Duplicate claim span in one case")
            seen_spans.add(span)
            if claim.get("label") not in LABELS:
                raise ValueError("Unknown faithfulness label")
            if not isinstance(claim.get("rationale"), str) or not claim["rationale"].strip():
                raise ValueError("Every claim needs a reviewer rationale")
            evidence = claim.get("evidence")
            _validate_evidence(evidence, sources[case_id])
            if claim["label"] in {"supported", "contradicted"} and not evidence:
                raise ValueError("Supported/contradicted claims require source evidence")
    if found != expected:
        raise ValueError(f"Review is missing cases: {sorted(expected - found)}")
    return True


def score_review(report, review):
    """Score only cases a human has explicitly marked fully reviewed."""
    validate_review(report, review)
    complete = [case for case in review["cases"] if case["complete"]]
    counts = Counter(
        claim["label"]
        for case in complete
        for claim in case["claims"]
    )
    total = sum(counts.values())
    alignment = Counter(case["status_alignment"] for case in complete)
    return {
        "status": (
            "pending" if not complete
            else "complete" if len(complete) == len(review["cases"])
            else "partial"
        ),
        "reviewed_cases": len(complete),
        "eligible_cases": len(review["cases"]),
        "reviewed_claims": total,
        "claim_counts": {label: counts[label] for label in sorted(LABELS)},
        "supported_claim_fraction": round(counts["supported"] / total, 3) if total else None,
        "unsupported_or_unverifiable_fraction": round(
            (counts["contradicted"] + counts["unverifiable"]) / total, 3
        ) if total else None,
        "status_alignment": {
            label: alignment[label] for label in (
                "consistent", "inconsistent"
            )
        },
        "note": (
            "Human-reviewed claim labels only. Evidence pointers and quotes are "
            "validated for existence; support/contradiction judgments are not "
            "automatically proven. Incomplete cases are excluded."
        ),
    }
