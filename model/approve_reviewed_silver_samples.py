"""Explicitly approve individual silver samples after human inspection."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingScenario


def parse_run_ids(raw: str) -> list[int]:
    try:
        values = [int(value.strip()) for value in raw.split(",") if value.strip()]
    except ValueError as exc:
        raise ValueError("--run-ids must be comma-separated positive integers") from exc
    if not values or any(value <= 0 for value in values):
        raise ValueError("--run-ids must contain at least one positive integer")
    return list(dict.fromkeys(values))


def eligible_for_human_silver_approval(label: TrainingAutoLabel, scenario: TrainingScenario) -> bool:
    if label.label != "silver" or label.approval_status != "pending" or scenario.scenario_type != "matrix":
        return False
    decision = json.loads(label.decision_json)
    if decision.get("hard_errors"):
        return False
    return not any(
        outcome.get("rubric", {}).get("contradicted_claims")
        for outcome in decision.get("judge_outcomes", [])
    )


def approve_samples(batch: str, run_ids: list[int]) -> int:
    db = SessionLocal()
    try:
        rows = (
            db.query(TrainingAutoLabel, TrainingScenario)
            .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
            .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
            .filter(TrainingAutoLabel.run_id.in_(run_ids))
            .all()
        )
        by_run_id = {label.run_id: (label, scenario) for label, scenario in rows}
        missing = sorted(set(run_ids) - set(by_run_id))
        if missing:
            raise ValueError(f"training runs not found: {missing}")
        invalid = [run_id for run_id in run_ids if not eligible_for_human_silver_approval(*by_run_id[run_id])]
        if invalid:
            raise ValueError(f"runs are not pending, contradiction-free silver matrix samples: {invalid}")
        for run_id in run_ids:
            label, _ = by_run_id[run_id]
            label.approval_status = "approved"
            label.approval_batch = batch
            label.approval_source = "human_silver_review"
            label.approved_at = datetime.utcnow()
        db.commit()
        return len(run_ids)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve manually inspected silver samples for SFT export")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--run-ids", required=True, help="Comma-separated IDs from export_silver_review_queue.py")
    parser.add_argument("--approve", action="store_true", help="Required acknowledgement that every listed sample was inspected")
    args = parser.parse_args()
    if not args.approve:
        raise SystemExit("Refusing to approve without --approve after manual inspection")
    if len(args.batch.strip()) < 3:
        raise SystemExit("--batch must be a stable, descriptive batch identifier")
    try:
        run_ids = parse_run_ids(args.run_ids)
        count = approve_samples(args.batch.strip(), run_ids)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"batch": args.batch.strip(), "approved": count, "run_ids": run_ids}, ensure_ascii=False))


if __name__ == "__main__":
    main()
