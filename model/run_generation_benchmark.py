"""Call TripCraft's public generation API for benchmark scenarios and persist offline runs."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


async def run_cases(cases: list[dict[str, Any]], api_base: str, concurrency: int) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=180) as client:
        async def run_one(case: dict[str, Any]) -> dict[str, Any]:
            started = time.perf_counter()
            async with semaphore:
                try:
                    response = await client.post(f"{api_base.rstrip('/')}/api/generate", json=case["request"])
                    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    if not response.is_success:
                        payload = {"itinerary": {"error": f"HTTP_{response.status_code}"}, "verification": {}}
                except (httpx.HTTPError, ValueError) as exc:
                    payload = {"itinerary": {"error": str(exc)}, "verification": {}}
            return {
                **case,
                "response": payload,
                "latency_ms": round((time.perf_counter() - started) * 1000),
            }
        return await asyncio.gather(*(run_one(case) for case in cases))


def persist_runs(records: list[dict[str, Any]]) -> int:
    from database.models import SessionLocal, TrainingGenerationRun, TrainingScenario

    db = SessionLocal()
    persisted = 0
    try:
        for record in records:
            scenario = db.query(TrainingScenario).filter(TrainingScenario.scenario_key == record["scenario_id"]).first()
            if scenario is None:
                scenario = TrainingScenario(
                    scenario_key=record["scenario_id"],
                    request_json=json.dumps(record["request"], ensure_ascii=False),
                    bucket_json=json.dumps(record.get("bucket", {}), ensure_ascii=False),
                    expected_risks=",".join(record.get("expected_risks", [])) or None,
                    matrix_version=record["matrix_version"],
                    scenario_type=record.get("scenario_type", "matrix"),
                    random_seed=record["seed"],
                )
                db.add(scenario)
                db.flush()
            response = record["response"]
            db.add(TrainingGenerationRun(
                scenario_id=scenario.id,
                generator_model=str(response.get("model_version") or "none"),
                response_json=json.dumps(response, ensure_ascii=False),
                verification_json=json.dumps(response.get("verification"), ensure_ascii=False) if response.get("verification") else None,
                generation_source=response.get("generation_source"),
                validation_status=response.get("validation_status"),
                fallback_reason=response.get("fallback_reason"),
                latency_ms=record["latency_ms"],
                output_hash=_hash(response),
            ))
            persisted += 1
        db.commit()
        return persisted
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible TripCraft generation benchmarks")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--persist", action="store_true", help="Persist runs in training_* tables, never SavedTrip")
    args = parser.parse_args()

    records = asyncio.run(run_cases(_read_jsonl(args.input), args.api_base, max(1, min(args.concurrency, 8))))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    persisted = persist_runs(records) if args.persist else 0
    print(json.dumps({"runs": len(records), "persisted": persisted, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
