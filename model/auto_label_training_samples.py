"""Apply hard gates and independent judge models to persisted synthetic generation runs."""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database.models import SessionLocal, TrainingAutoLabel, TrainingEvidence, TrainingGenerationRun, TrainingJudgment, TrainingScenario
from services.training_judge_service import RULE_VERSION, build_configured_judge_providers, judge_generation
from trigger_silver_repair import trigger_if_needed


AUTO_APPROVAL_SOURCE = "automated_evidence_consensus"


def _providers() -> list[tuple[str, Any]]:
    return build_configured_judge_providers()


def _pending_runs(
    db,
    limit: int | None,
    min_run_id: int | None = None,
) -> list[tuple[TrainingGenerationRun, TrainingScenario]]:
    query = (
        db.query(TrainingGenerationRun, TrainingScenario)
        .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
        .outerjoin(TrainingAutoLabel, TrainingAutoLabel.run_id == TrainingGenerationRun.id)
        .filter(TrainingAutoLabel.id.is_(None))
        .order_by(TrainingGenerationRun.id)
    )
    if min_run_id is not None:
        query = query.filter(TrainingGenerationRun.id >= min_run_id)
    return query.limit(limit).all() if limit else query.all()


async def label_runs(
    runs: list[tuple[TrainingGenerationRun, TrainingScenario]],
    providers: list[tuple[str, Any]],
    concurrency: int = 2,
) -> list[tuple[TrainingGenerationRun, Any]]:
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 8)))

    async def label_one(run: TrainingGenerationRun, scenario: TrainingScenario):
        response = json.loads(run.response_json)
        request = json.loads(scenario.request_json)
        async with semaphore:
            return run, await judge_generation(response, request, providers)

    return list(await asyncio.gather(*(label_one(run, scenario) for run, scenario in runs)))


def eligible_for_auto_approval(decision: Any) -> bool:
    """Defence in depth: hard errors and judge availability still gate promotion."""
    if decision.label != "auto_gold_candidate" or decision.confidence < settings.auto_eval_auto_approve_confidence:
        return False
    blocking_errors = [error for error in decision.hard_errors if error != "REPAIR_REQUIRED"]
    if blocking_errors or len(decision.judge_outcomes) < 2:
        return False
    for outcome in decision.judge_outcomes[:2]:
        if outcome.rubric is None or outcome.rubric.get("contradicted_claims"):
            return False
        if outcome.rubric.get("unverified_claims") and not settings.auto_eval_allow_unverified_claims:
            return False
    return True


def persist_labels(
    db,
    decisions: list[tuple[TrainingGenerationRun, Any]],
    approval_batch: str | None = None,
) -> list[dict[str, Any]]:
    output = []
    batch = approval_batch or f"auto-evidence-{datetime.utcnow():%Y%m%d}"
    for run, decision in decisions:
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
        label = TrainingAutoLabel(
            run_id=run.id,
            label=decision.label,
            confidence=decision.confidence,
            rule_version=RULE_VERSION,
            decision_json=json.dumps(decision.as_record(), ensure_ascii=False),
            approval_status="pending",
        )
        if settings.auto_eval_auto_approve and eligible_for_auto_approval(decision):
            label.approval_status = "approved"
            label.approval_batch = batch
            label.approval_source = AUTO_APPROVAL_SOURCE
            label.approved_at = datetime.utcnow()
        db.add(label)
        output.append({
            "run_id": run.id,
            "approval_status": label.approval_status,
            "approval_batch": label.approval_batch,
            **decision.as_record(),
        })
    db.commit()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-label offline TripCraft benchmark runs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-run-id", type=int, default=None, help="Only label runs at or after this database ID")
    parser.add_argument("--approval-batch", default=None, help="Automatic approval batch name when AUTO_EVAL_AUTO_APPROVE=true")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of generation runs evaluated concurrently")
    parser.add_argument("--force", action="store_true", help="Allow an explicit run when AUTO_EVAL_ENABLED=false")
    args = parser.parse_args()
    if not settings.auto_eval_enabled and not args.force:
        raise SystemExit("AUTO_EVAL_ENABLED=false; set it after calibration or pass --force for an explicit local experiment")

    db = SessionLocal()
    try:
        runs = _pending_runs(db, args.limit, args.min_run_id)
        providers = _providers()
        decisions = asyncio.run(label_runs(runs, providers, args.concurrency))
        output = persist_labels(db, decisions, args.approval_batch)
    finally:
        db.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for item in output:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for item in output:
        counts[item["label"]] = counts.get(item["label"], 0) + 1
    approved = sum(item["approval_status"] == "approved" for item in output)
    trigger = trigger_if_needed()
    print(json.dumps({"labeled": len(output), "approved": approved, "counts": counts, "output": str(args.output), "repair_trigger": trigger}, ensure_ascii=False))


if __name__ == "__main__":
    main()
