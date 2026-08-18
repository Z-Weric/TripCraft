"""Backfill automatic approval for evidence-complete auto-gold candidates."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingScenario
from auto_label_training_samples import AUTO_APPROVAL_SOURCE, eligible_for_auto_approval
from services.training_judge_service import AutoLabelDecision, JudgeOutcome


def decision_from_record(label: TrainingAutoLabel) -> AutoLabelDecision:
    record = json.loads(label.decision_json)
    outcomes = [JudgeOutcome(**item) for item in record.get("judge_outcomes", [])]
    return AutoLabelDecision(
        label=record.get("label", label.label),
        confidence=float(record.get("confidence", label.confidence or 0)),
        rule_version=record.get("rule_version", label.rule_version),
        hard_errors=record.get("hard_errors", []),
        judge_outcomes=outcomes,
        evidence=record.get("evidence", []),
    )


def approve_existing(batch: str, min_confidence: float) -> int:
    db = SessionLocal()
    try:
        rows = (
            db.query(TrainingAutoLabel, TrainingScenario)
            .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
            .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
            .filter(
                TrainingAutoLabel.approval_status == "pending",
                TrainingAutoLabel.label == "auto_gold_candidate",
                TrainingAutoLabel.confidence >= min_confidence,
                TrainingScenario.scenario_type == "matrix",
            )
            .all()
        )
        approved = 0
        original_threshold = settings.auto_eval_auto_approve_confidence
        settings.auto_eval_auto_approve_confidence = min_confidence
        try:
            for label, _ in rows:
                if not eligible_for_auto_approval(decision_from_record(label)):
                    continue
                label.approval_status = "approved"
                label.approval_batch = batch
                label.approval_source = AUTO_APPROVAL_SOURCE
                label.approved_at = datetime.utcnow()
                approved += 1
        finally:
            settings.auto_eval_auto_approve_confidence = original_threshold
        db.commit()
        return approved
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatically approve evidence-complete auto-gold candidates")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--min-confidence", type=float, default=None)
    args = parser.parse_args()
    threshold = settings.auto_eval_auto_approve_confidence if args.min_confidence is None else args.min_confidence
    if not 0 <= threshold <= 1:
        raise SystemExit("--min-confidence must be between 0 and 1")
    count = approve_existing(args.batch.strip(), threshold)
    print(json.dumps({"batch": args.batch.strip(), "approved": count, "min_confidence": threshold}, ensure_ascii=False))


if __name__ == "__main__":
    main()
