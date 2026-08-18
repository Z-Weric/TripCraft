"""Reclassify existing pending labels after a rubric-policy change.

This is deliberately local and does not call any model. It reuses the two judge
outcomes already stored in decision_json, preserving the original evidence and
lineage while applying the current promotion policy.
"""

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
from database.models import SessionLocal, TrainingAutoLabel
from services.training_judge_service import (
    AutoLabelDecision,
    JudgeOutcome,
    RULE_VERSION,
    aggregate_judgments,
)
from auto_label_training_samples import eligible_for_auto_approval


def _decision_from_record(record: dict) -> AutoLabelDecision:
    outcomes = []
    for item in record.get("judge_outcomes", []):
        rubric = item.get("rubric")
        if rubric is not None:
            # Backward compatibility with labels written before the terminology
            # changed from unsupported_claims to contradicted/unverified_claims.
            rubric = dict(rubric)
            if "contradicted_claims" not in rubric:
                rubric["contradicted_claims"] = list(rubric.get("unsupported_claims", []))
            rubric.setdefault("unverified_claims", [])
        outcomes.append(JudgeOutcome(
            provider=str(item.get("provider") or "unknown"),
            model=str(item.get("model") or "unknown"),
            rubric=rubric,
            prompt_hash=str(item.get("prompt_hash") or "legacy"),
            latency_ms=item.get("latency_ms"),
            error_message=item.get("error_message"),
        ))
    return aggregate_judgments(record.get("hard_errors", []), outcomes)


def reclassify(batch: str, limit: int | None = None) -> dict[str, int | str]:
    db = SessionLocal()
    counts = {"examined": 0, "changed": 0, "auto_gold_candidate": 0, "approved": 0, "still_silver": 0}
    try:
        query = (
            db.query(TrainingAutoLabel)
            .filter(TrainingAutoLabel.approval_status == "pending", TrainingAutoLabel.label == "silver")
            .order_by(TrainingAutoLabel.id)
        )
        if limit:
            query = query.limit(limit)
        for label in query.all():
            counts["examined"] += 1
            try:
                record = json.loads(label.decision_json or "{}")
                decision = _decision_from_record(record)
            except (TypeError, ValueError, json.JSONDecodeError):
                counts["still_silver"] += 1
                continue
            label.label = decision.label
            label.confidence = decision.confidence
            label.rule_version = RULE_VERSION
            label.decision_json = json.dumps(
                AutoLabelDecision(
                    decision.label,
                    decision.confidence,
                    RULE_VERSION,
                    decision.hard_errors,
                    decision.judge_outcomes,
                    record.get("evidence", []),
                ).as_record(),
                ensure_ascii=False,
            )
            counts["changed"] += 1
            if decision.label == "auto_gold_candidate":
                counts["auto_gold_candidate"] += 1
                if settings.auto_eval_auto_approve and eligible_for_auto_approval(decision):
                    label.approval_status = "approved"
                    label.approval_batch = batch
                    label.approval_source = "automated_relaxed_policy"
                    label.approved_at = datetime.utcnow()
                    counts["approved"] += 1
            else:
                counts["still_silver"] += 1
        db.commit()
    finally:
        db.close()
    return {**counts, "batch": batch, "rule_version": RULE_VERSION}


def main() -> None:
    parser = argparse.ArgumentParser(description="Reclassify pending silver labels with the current relaxed policy")
    parser.add_argument("--batch", default=f"auto-relaxed-{datetime.utcnow():%Y%m%d}")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if not 0 <= settings.auto_eval_accept_confidence <= 1:
        raise SystemExit("AUTO_EVAL_ACCEPT_CONFIDENCE must be between 0 and 1")
    print(json.dumps(reclassify(args.batch, args.limit), ensure_ascii=False))


if __name__ == "__main__":
    main()
