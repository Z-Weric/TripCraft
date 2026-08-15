"""Apply hard gates and independent judge models to persisted synthetic generation runs."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingJudgment, TrainingScenario
from services.training_judge_service import RULE_VERSION, build_configured_judge_providers, judge_generation


def _providers() -> list[tuple[str, Any]]:
    return build_configured_judge_providers()


def _pending_runs(db, limit: int | None) -> list[tuple[TrainingGenerationRun, TrainingScenario]]:
    query = (
        db.query(TrainingGenerationRun, TrainingScenario)
        .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
        .outerjoin(TrainingAutoLabel, TrainingAutoLabel.run_id == TrainingGenerationRun.id)
        .filter(TrainingAutoLabel.id.is_(None))
        .order_by(TrainingGenerationRun.id)
    )
    return query.limit(limit).all() if limit else query.all()


async def label_runs(runs: list[tuple[TrainingGenerationRun, TrainingScenario]], providers: list[tuple[str, Any]]) -> list[tuple[TrainingGenerationRun, Any]]:
    results = []
    for run, scenario in runs:
        response = json.loads(run.response_json)
        request = json.loads(scenario.request_json)
        results.append((run, await judge_generation(response, request, providers)))
    return results


def persist_labels(db, decisions: list[tuple[TrainingGenerationRun, Any]]) -> list[dict[str, Any]]:
    output = []
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
        db.add(TrainingAutoLabel(
            run_id=run.id,
            label=decision.label,
            confidence=decision.confidence,
            rule_version=RULE_VERSION,
            decision_json=json.dumps(decision.as_record(), ensure_ascii=False),
        ))
        output.append({"run_id": run.id, **decision.as_record()})
    db.commit()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-label offline TripCraft benchmark runs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Allow an explicit run when AUTO_EVAL_ENABLED=false")
    args = parser.parse_args()
    if not settings.auto_eval_enabled and not args.force:
        raise SystemExit("AUTO_EVAL_ENABLED=false; set it after calibration or pass --force for an explicit local experiment")

    db = SessionLocal()
    try:
        runs = _pending_runs(db, args.limit)
        providers = _providers()
        decisions = asyncio.run(label_runs(runs, providers))
        output = persist_labels(db, decisions)
    finally:
        db.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for item in output:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for item in output:
        counts[item["label"]] = counts.get(item["label"], 0) + 1
    print(json.dumps({"labeled": len(output), "counts": counts, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
