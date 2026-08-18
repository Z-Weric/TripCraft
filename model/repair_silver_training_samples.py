"""Repair pending silver candidates without regenerating their immutable plans."""

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODEL_DIR = ROOT / "model"
for path in (BACKEND, MODEL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from config import settings
from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingScenario
from services.training_judge_service import build_configured_judge_providers, judge_generation
from services.training_repair_service import build_repair_provider, repair_narrative
from auto_label_training_samples import persist_labels


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _pending_sources(
    db,
    min_run_id: int | None,
    limit: int | None,
    only_unrepaired: bool = False,
    run_ids: list[int] | None = None,
):
    query = (
        db.query(TrainingAutoLabel, TrainingGenerationRun, TrainingScenario)
        .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
        .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
        .filter(
            TrainingAutoLabel.label == "silver",
            TrainingAutoLabel.approval_status == "pending",
            TrainingScenario.scenario_type == "matrix",
        )
        .order_by(TrainingAutoLabel.confidence.desc(), TrainingAutoLabel.id)
    )
    if run_ids:
        query = query.filter(TrainingGenerationRun.id.in_(run_ids))
    else:
        query = query.filter(
            (TrainingGenerationRun.repair_iteration == 0) | (TrainingGenerationRun.repair_iteration.is_(None))
        )
    if min_run_id is not None:
        query = query.filter(TrainingGenerationRun.id >= min_run_id)
    rows = query.all() if only_unrepaired else (query.limit(limit).all() if limit else query.all())
    if only_unrepaired:
        source_ids = [source_run.id for _, source_run, _ in rows]
        child_parent_ids = {
            parent_id
            for (parent_id,) in db.query(TrainingGenerationRun.parent_run_id)
            .filter(TrainingGenerationRun.parent_run_id.in_(source_ids))
            .all()
            if parent_id is not None
        }
        rows = [row for row in rows if row[1].id not in child_parent_ids]
        return rows[:limit] if limit else rows
    return rows


def _existing_child(db, parent_run_id: int, iteration: int):
    return (
        db.query(TrainingGenerationRun)
        .filter(TrainingGenerationRun.parent_run_id == parent_run_id, TrainingGenerationRun.repair_iteration == iteration)
        .order_by(TrainingGenerationRun.id.desc())
        .first()
    )


async def repair_one(db, source_run, scenario, provider, judges, max_iterations: int, approval_batch: str) -> list[dict[str, Any]]:
    request = json.loads(scenario.request_json)
    current_run = source_run
    current_label = db.query(TrainingAutoLabel).filter(TrainingAutoLabel.run_id == current_run.id).one()
    results: list[dict[str, Any]] = []
    for _ in range(max_iterations):
        if current_label.label != "silver" or current_label.approval_status != "pending":
            break
        iteration = (current_run.repair_iteration or 0) + 1
        existing = _existing_child(db, current_run.id, iteration)
        if existing is not None:
            current_run = existing
            current_label = db.query(TrainingAutoLabel).filter(TrainingAutoLabel.run_id == current_run.id).first()
            # A process can be interrupted after the child run commit but before
            # its judgment label commit. Resume by judging that immutable child
            # instead of aborting the whole batch.
            if current_label is None:
                existing_response = json.loads(current_run.response_json)
                existing_decision = await judge_generation(existing_response, request, judges)
                persisted = persist_labels(db, [(current_run, existing_decision)], approval_batch)
                persisted[0]["source_run_id"] = source_run.id
                persisted[0]["repair_iteration"] = current_run.repair_iteration
                results.extend(persisted)
                current_label = db.query(TrainingAutoLabel).filter(TrainingAutoLabel.run_id == current_run.id).one()
            continue
        response = json.loads(current_run.response_json)
        decision = json.loads(current_label.decision_json)
        repaired_itinerary, repair_error, prompt_hash = await repair_narrative(provider, request, response.get("itinerary", {}), decision)
        if repaired_itinerary is None:
            results.append({"source_run_id": source_run.id, "iteration": iteration, "error": repair_error})
            break
        child_response = dict(response)
        child_response["itinerary"] = repaired_itinerary
        child_response["model_version"] = provider.model_id
        child_response["generation_source"] = "llm_repaired"
        child_response["validation_status"] = "repaired"
        child_response["fallback_reason"] = None
        child = TrainingGenerationRun(
            scenario_id=current_run.scenario_id,
            parent_run_id=current_run.id,
            repair_iteration=iteration,
            generator_model=provider.model_id,
            response_json=json.dumps(child_response, ensure_ascii=False),
            verification_json=json.dumps(child_response.get("verification"), ensure_ascii=False),
            generation_source="llm_repaired",
            validation_status="repaired",
            fallback_reason=None,
            latency_ms=None,
            output_hash=_hash(child_response),
        )
        db.add(child)
        db.commit()
        child_decision = await judge_generation(child_response, request, judges)
        persisted = persist_labels(db, [(child, child_decision)], approval_batch)
        persisted[0]["source_run_id"] = source_run.id
        persisted[0]["repair_iteration"] = iteration
        persisted[0]["repair_prompt_hash"] = prompt_hash
        results.extend(persisted)
        current_run = child
        current_label = db.query(TrainingAutoLabel).filter(TrainingAutoLabel.run_id == child.id).one()
        if current_label.approval_status == "approved":
            break
    return results


async def run_repairs(rows, max_iterations: int, approval_batch: str) -> list[dict[str, Any]]:
    provider = build_repair_provider()
    if not provider.available:
        raise RuntimeError(f"repair provider unavailable: {provider.model_id}")
    judges = build_configured_judge_providers()
    db = SessionLocal()
    results: list[dict[str, Any]] = []
    try:
        for _, source_run, scenario in rows:
            results.extend(await repair_one(db, source_run, scenario, provider, judges, max_iterations, approval_batch))
    finally:
        db.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair and rejudge pending silver training samples")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-run-id", type=int, default=None)
    parser.add_argument(
        "--run-ids",
        default=None,
        help="Comma-separated pending silver run IDs to repair directly; supports retrying leaf repair versions.",
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--approval-batch", default="auto-evidence-20260816")
    parser.add_argument("--only-unrepaired", action="store_true", help="Skip silver sources that already have a repair child")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not settings.auto_eval_enabled and not args.force:
        raise SystemExit("AUTO_EVAL_ENABLED=false; pass --force for an explicit repair run")
    max_iterations = settings.auto_eval_repair_max_iterations if args.max_iterations is None else args.max_iterations
    if not 1 <= max_iterations <= 3:
        raise SystemExit("--max-iterations must be between 1 and 3")
    db = SessionLocal()
    try:
        try:
            run_ids = [int(value.strip()) for value in args.run_ids.split(",") if value.strip()] if args.run_ids else None
        except ValueError as exc:
            raise SystemExit("--run-ids must contain comma-separated integer IDs") from exc
        rows = _pending_sources(db, args.min_run_id, args.limit, args.only_unrepaired, run_ids)
    finally:
        db.close()
    results = asyncio.run(run_repairs(rows, max_iterations, args.approval_batch))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for item in results:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    approved = sum(item.get("approval_status") == "approved" for item in results)
    print(json.dumps({"sources": len(rows), "repair_results": len(results), "approved": approved, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
