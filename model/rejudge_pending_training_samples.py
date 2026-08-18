"""Retry pending zero-confidence labels with the configured independent judges."""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database.models import (
    SessionLocal,
    TrainingAutoLabel,
    TrainingEvidence,
    TrainingGenerationRun,
    TrainingJudgment,
    TrainingScenario,
)
from services.training_judge_service import RULE_VERSION, build_configured_judge_providers, judge_generation
from auto_label_training_samples import eligible_for_auto_approval


def _pending(db, min_run_id: int | None, max_run_id: int | None, limit: int | None):
    query = (
        db.query(TrainingAutoLabel, TrainingGenerationRun, TrainingScenario)
        .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
        .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
        .filter(
            TrainingAutoLabel.approval_status == "pending",
            TrainingAutoLabel.label == "silver",
            TrainingAutoLabel.confidence == 0,
        )
        .order_by(TrainingGenerationRun.id)
    )
    if min_run_id is not None:
        query = query.filter(TrainingGenerationRun.id >= min_run_id)
    if max_run_id is not None:
        query = query.filter(TrainingGenerationRun.id <= max_run_id)
    return query.limit(limit).all() if limit else query.all()


async def rejudge(rows, batch: str, concurrency: int) -> dict[str, int | str]:
    providers = build_configured_judge_providers()
    db = SessionLocal()
    counts = {"examined": 0, "rejudged": 0, "approved": 0, "silver": 0, "negative": 0, "errors": 0}
    evidence_enabled = settings.auto_eval_evidence_enabled
    # Bocha is not configured in this environment. Avoid waiting through an
    # evidence/debate timeout during a judge-key retry; unknown claims remain
    # allowed by the active relaxed policy and are preserved in the rubric.
    settings.auto_eval_evidence_enabled = False
    try:
        semaphore = asyncio.Semaphore(max(1, min(concurrency, 8)))

        async def evaluate(row):
            label, run, scenario = row
            try:
                response = json.loads(run.response_json)
                request = json.loads(scenario.request_json)
                async with semaphore:
                    return row, await judge_generation(response, request, providers), None
            except Exception as exc:
                return row, None, exc

        evaluated = await asyncio.gather(*(evaluate(row) for row in rows))
        for (label, run, scenario), decision, evaluation_error in evaluated:
            counts["examined"] += 1
            if evaluation_error is not None or decision is None:
                counts["errors"] += 1
                continue
            try:
                # The selection session is closed before async judging starts;
                # attach the rows to the write session before mutating labels.
                label = db.get(TrainingAutoLabel, label.id)
                run = db.get(TrainingGenerationRun, run.id)
                counts["rejudged"] += 1
                for outcome in decision.judge_outcomes:
                    db.add(TrainingJudgment(
                        run_id=run.id,
                        judge_provider=outcome.provider,
                        judge_model=outcome.model,
                        rubric_json=json.dumps(outcome.rubric, ensure_ascii=False) if outcome.rubric else "{}",
                        prompt_hash=outcome.prompt_hash,
                        latency_ms=outcome.latency_ms,
                        error_message=outcome.error_message,
                    ))
                for evidence in decision.evidence:
                    db.add(TrainingEvidence(
                        run_id=run.id,
                        claim_hash=evidence["claim_hash"],
                        claim_text=evidence["claim"],
                        query_text=evidence["query"],
                        provider=evidence["provider"],
                        sources_json=json.dumps(evidence["sources"], ensure_ascii=False),
                        retrieval_error=evidence.get("error"),
                    ))
                label.label = decision.label
                label.confidence = decision.confidence
                label.rule_version = RULE_VERSION
                label.decision_json = json.dumps(decision.as_record(), ensure_ascii=False)
                label.approval_status = "pending"
                label.approval_batch = None
                label.approval_source = None
                label.approved_at = None
                if settings.auto_eval_auto_approve and eligible_for_auto_approval(decision):
                    label.approval_status = "approved"
                    label.approval_batch = batch
                    label.approval_source = "automated_rejudge"
                    label.approved_at = datetime.utcnow()
                    counts["approved"] += 1
                counts[decision.label] = counts.get(decision.label, 0) + 1
                db.commit()
            except Exception:
                db.rollback()
                counts["errors"] += 1
        return {**counts, "batch": batch, "rule_version": RULE_VERSION}
    finally:
        settings.auto_eval_evidence_enabled = evidence_enabled
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry zero-confidence pending labels")
    parser.add_argument("--min-run-id", type=int, default=None)
    parser.add_argument("--max-run-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--batch", default=f"auto-rejudge-{datetime.utcnow():%Y%m%d}")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        rows = _pending(db, args.min_run_id, args.max_run_id, args.limit)
    finally:
        db.close()
    print(json.dumps(asyncio.run(rejudge(rows, args.batch, args.concurrency)), ensure_ascii=False))


if __name__ == "__main__":
    main()
