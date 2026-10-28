"""Unit tests for targeted evaluation-case selection (no model required)."""
import pytest

from scripts.run_answer_eval import select_cases


CASES = [
    {"id": "POLICY_REPORTING"},
    {"id": "UNKNOWN_GPS"},
    {"id": "UNVERIFIED_COMPENSATION"},
]


def test_select_single_case():
    assert select_cases(CASES, ["UNKNOWN_GPS"]) == [CASES[1]]


def test_select_multiple_cases_preserves_dataset_order():
    selected = select_cases(
        CASES,
        ["UNVERIFIED_COMPENSATION", "POLICY_REPORTING"],
    )
    assert [item["id"] for item in selected] == [
        "POLICY_REPORTING", "UNVERIFIED_COMPENSATION",
    ]


def test_select_unknown_case_is_rejected():
    with pytest.raises(ValueError, match="Unknown evaluation case"):
        select_cases(CASES, ["NOT_A_CASE"])


def test_limit_without_filter():
    assert select_cases(CASES, limit=2) == CASES[:2]
