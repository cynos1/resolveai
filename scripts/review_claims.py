"""Create and score human claim-level reviews of a ResolveAI answer report.

From the repository root:
    python scripts/review_claims.py init
    python scripts/review_claims.py score

Both commands use the latest answer_eval_*.json in reports/ unless --report
is supplied. The original report is never modified.
"""
import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.claim_evaluation import make_review_template, score_review


REPORTS = ROOT / "reports"


def pick_report(explicit=None):
    if explicit is not None:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    available = sorted(REPORTS.glob("answer_eval_*.json"))
    if not available:
        raise FileNotFoundError(
            "No answer evaluation report found. Run "
            "python scripts/run_answer_eval.py first."
        )
    return available[-1]


def review_path(report):
    return report.parent / ("claim_review_" + report.stem + ".json")


def score_path(report):
    return report.parent / ("claim_scores_" + report.stem + ".json")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def init_review(report):
    template = make_review_template(read_json(report))
    target = review_path(report)
    # Do not destroy existing annotations.
    with target.open("x", encoding="utf-8") as handle:
        json.dump(template, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print("Created review template:", target)
    print("Eligible answer cases:", len(template["cases"]))
    print("All cases start incomplete; no faithfulness score has been assigned.")
    print("Edit the template, then run: python scripts/review_claims.py score")
    return target


def score_existing_review(report):
    path = review_path(report)
    if not path.is_file():
        raise FileNotFoundError(
            f"Review file not found: {path}. Run the init command first."
        )
    summary = score_review(read_json(report), read_json(path))
    target = score_path(report)
    target.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Review status:", summary["status"])
    print("Complete cases:", summary["reviewed_cases"], "/", summary["eligible_cases"])
    print("Reviewed atomic claims:", summary["reviewed_claims"])
    print("Label counts:", summary["claim_counts"])
    if summary["supported_claim_fraction"] is None:
        print("Claim support score: not available (no completed human reviews)")
    else:
        print("Supported-claim fraction:", f'{summary["supported_claim_fraction"]:.1%}')
    print("Saved summary:", target)
    print(summary["note"])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for cmd in ("init", "score"):
        sub = commands.add_parser(cmd)
        sub.add_argument(
            "--report",
            help="Path to an answer_eval_*.json; defaults to latest in reports/",
        )
    args = parser.parse_args()
    try:
        report = pick_report(args.report)
        if args.command == "init":
            init_review(report)
        else:
            score_existing_review(report)
    except (FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
