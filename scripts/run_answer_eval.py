"""Run grounded-answer evaluations against an existing ResolveAI API server.

Examples (from repository root):
    python scripts/run_answer_eval.py --limit 2
    python scripts/run_answer_eval.py
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.answer_evaluation import evaluate_response, summarize_results


DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "answer_cases.json"
REPORTS_DIR = PROJECT_ROOT / "reports"


def call_api(base_url, case, timeout=360):
    """Return (HTTP status, decoded body) for one test case."""
    request = Request(
        url=base_url.rstrip("/") + "/investigations/answer",
        data=json.dumps({
            "booking_reference": case["booking_reference"],
            "question": case["question"],
            "top_k": 3,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(
                response.read().decode("utf-8")
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"detail": body}


def select_cases(cases, case_ids=None, limit=None):
    """Select named cases or a prefix, without changing dataset order."""
    if case_ids:
        requested = set(case_ids)
        available = {case["id"] for case in cases}
        unknown = sorted(requested - available)
        if unknown:
            raise ValueError("Unknown evaluation case(s): " + ", ".join(unknown))
        cases = [case for case in cases if case["id"] in requested]
    if limit is not None:
        cases = cases[:limit]
    return cases


def run_evaluation(base_url, limit=None, case_ids=None):
    """Execute cases sequentially and write complete results locally."""
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Expected an evaluation JSON array")
    cases = select_cases(cases, case_ids=case_ids, limit=limit)

    results = []

    for number, case in enumerate(cases, start=1):
        print(f"\n[{number}/{len(cases)}] {case['id']}", flush=True)
        try:
            http_status, response = call_api(base_url, case)
        except (URLError, TimeoutError, OSError) as exc:
            http_status, response = 0, {"error": str(exc)}
            print(f"Request could not be completed: {exc}")

        evaluation = evaluate_response(case, http_status, response)
        results.append({
            "case": case,
            "http_status": http_status,
            "response": response,
            "evaluation": evaluation,
        })

        print("HTTP status:", http_status)
        print("Deterministic result:", "PASS" if evaluation["passed"] else "FAIL")
        for name, passed in evaluation["checks"].items():
            if not passed:
                print("  Failed check:", name)
        if http_status == 200 and isinstance(response, dict):
            print("Answer:", response.get("answer", ""))
            print("Citations:", response.get("citations", []))
        if evaluation["manual_review_required"]:
            print("Needs factual review:", evaluation["review_focus"])

    summary = summarize_results(results)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": base_url.rstrip("/") + "/investigations/answer",
        "summary": summary,
        "results": results,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    report_path = REPORTS_DIR / f"answer_eval_{timestamp}.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 50)
    print("DETERMINISTIC EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Passed: {summary['passed_cases']}/{summary['total_cases']}")
    print(f"Pass rate: {summary['pass_rate']:.1%}")
    for name, rate in summary["check_pass_rates"].items():
        print(f"{name}: {rate:.1%}")
    print("Manual claim-level review needed for:",
          summary["manual_review_cases"], "cases")
    print("Report saved:", report_path)
    print(
        "NOTE: This pass rate measures API structure and declared "
        "expectations, not factual correctness."
    )

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--case",
        dest="case_ids",
        action="append",
        help="Run only this case ID; repeat --case for multiple cases.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        summary = run_evaluation(
            args.base_url,
            limit=args.limit,
            case_ids=args.case_ids,
        )
    except ValueError as exc:
        parser.error(str(exc))
    sys.exit(0 if summary["pass_rate"] == 1.0 else 1)
