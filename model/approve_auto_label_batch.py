"""Explicitly approve calibrated automatic candidates for an export batch."""

import argparse
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingScenario


def approve_batch(batch: str, min_confidence: float, limit: int | None = None) -> int:
    """Approve only normal, high-confidence candidates; challenge cases remain evaluation-only."""
    db = SessionLocal()
    try:
        query = (
            db.query(TrainingAutoLabel)
            .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
            .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
            .filter(
                TrainingAutoLabel.label == "auto_gold_candidate",
                TrainingAutoLabel.approval_status == "pending",
                TrainingAutoLabel.confidence >= min_confidence,
                TrainingScenario.scenario_type == "matrix",
            )
            .order_by(TrainingAutoLabel.id)
        )
        labels = query.limit(limit).all() if limit else query.all()
        for item in labels:
            item.approval_status = "approved"
            item.approval_batch = batch
            item.approval_source = "calibrated_auto"
            item.approved_at = datetime.utcnow()
        db.commit()
        return len(labels)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve a calibrated automatic-label batch for SFT export")
    parser.add_argument("--batch", required=True, help="Immutable batch name, for example auto-20260815-calibrated")
    parser.add_argument("--min-confidence", type=float, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--approve", action="store_true", help="Required acknowledgement after reviewing calibration metrics")
    args = parser.parse_args()
    if not args.approve:
        raise SystemExit("Refusing to approve without --approve. Review a representative calibration sample first.")
    if len(args.batch.strip()) < 3:
        raise SystemExit("--batch must be a stable, descriptive batch identifier")
    threshold = settings.auto_eval_accept_confidence if args.min_confidence is None else args.min_confidence
    if not 0 <= threshold <= 1:
        raise SystemExit("--min-confidence must be between 0 and 1")
    if threshold < settings.auto_eval_accept_confidence:
        raise SystemExit("--min-confidence cannot be lower than AUTO_EVAL_ACCEPT_CONFIDENCE")
    count = approve_batch(args.batch.strip(), threshold, args.limit)
    print({"batch": args.batch.strip(), "approved": count, "min_confidence": threshold})


if __name__ == "__main__":
    main()
