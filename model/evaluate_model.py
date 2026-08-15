"""Evaluate fixed TripCraft test samples against model predictions without network calls."""

import argparse
import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.response_validation_service import validate_narrative
from services.verify_service import verify_itinerary


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _parse_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _expected_itinerary(sample: dict[str, Any]) -> dict[str, Any]:
    itinerary = sample.get("expected_itinerary") or sample.get("itinerary")
    return itinerary if isinstance(itinerary, dict) else {}


def _known_pois(itinerary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("poi_id"),
            "name": item.get("spot"),
            "lat": item.get("lat"),
            "lng": item.get("lng"),
            "cost": item.get("cost"),
        }
        for day in itinerary.get("itinerary", [])
        if isinstance(day, dict)
        for item in day.get("items", [])
        if isinstance(item, dict)
    ]


def _poi_ids(payload: dict[str, Any]) -> list[int]:
    days = payload.get("days") if isinstance(payload.get("days"), list) else payload.get("itinerary", [])
    if not isinstance(days, list):
        return []
    return [
        item["poi_id"]
        for day in days
        if isinstance(day, dict)
        for item in day.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("poi_id"), int) and item["poi_id"] > 0
    ]


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


async def _evaluate_one(sample: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    expected = _expected_itinerary(sample)
    request = sample.get("request", {})
    allowed_poi_ids = set(sample.get("allowed_poi_ids") or _poi_ids(expected))
    raw = _parse_object(prediction.get("narrative")) or _parse_object(prediction.get("output")) or prediction.get("itinerary")
    raw = raw if isinstance(raw, dict) else None
    if raw is None:
        return {"schema_valid": False, "poi_references": 0, "poi_violations": 0, "business_valid": False, "no_repair": False}

    narrative_payload = raw if "days" in raw and "itinerary" not in raw else None
    if narrative_payload is not None:
        class Outcome:
            itinerary = type("Itinerary", (), {"itinerary": [type("Day", (), {"day": day.get("day"), "items": [type("Item", (), {"poi_id": item.get("poi_id")}) for item in day.get("items", [])]}) for day in expected.get("itinerary", [])]})

        # validate_narrative only needs the immutable day/POI order from the expected fact pack.
        narrative, errors = validate_narrative(narrative_payload, Outcome())
        schema_valid = narrative is not None and not errors
        poi_ids = _poi_ids(narrative_payload)
        # Narrative is restricted to prose; immutable planner facts remain the approved itinerary.
        itinerary = expected
    else:
        schema_valid = isinstance(raw.get("itinerary"), list) and isinstance(raw.get("days"), int)
        poi_ids = _poi_ids(raw)
        itinerary = raw

    violations = sum(1 for poi_id in poi_ids if poi_id not in allowed_poi_ids)
    report = await verify_itinerary(
        itinerary,
        int(request.get("budget") or expected.get("total_cost") or 1),
        _known_pois(expected),
        verify_external=False,
    )
    return {
        "schema_valid": schema_valid,
        "poi_references": len(poi_ids),
        "poi_violations": violations,
        "business_valid": bool(report["overall_valid"]),
        "no_repair": prediction.get("validation_status") == "valid" and not prediction.get("repair_attempted", False),
        "latency_ms": prediction.get("latency_ms") if isinstance(prediction.get("latency_ms"), (int, float)) else None,
    }


def evaluate_samples(test_samples: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    predictions_by_id = {str(item.get("id")): item for item in predictions if item.get("id") is not None}
    results = []
    missing_ids = []
    for sample in test_samples:
        sample_id = str(sample.get("id"))
        prediction = predictions_by_id.get(sample_id)
        if prediction is None:
            missing_ids.append(sample_id)
            continue
        results.append(asyncio.run(_evaluate_one(sample, prediction)))

    evaluated = len(results)
    poi_references = sum(result["poi_references"] for result in results)
    latencies = [float(result["latency_ms"]) for result in results if result["latency_ms"] is not None]
    return {
        "test_samples": len(test_samples),
        "evaluated_predictions": evaluated,
        "missing_prediction_ids": missing_ids,
        "schema_valid_rate": sum(result["schema_valid"] for result in results) / evaluated if evaluated else 0,
        "allow_listed_poi_violation_rate": sum(result["poi_violations"] for result in results) / poi_references if poi_references else 0,
        "business_rule_pass_rate": sum(result["business_valid"] for result in results) / evaluated if evaluated else 0,
        "no_repair_rate": sum(result["no_repair"] for result in results) / evaluated if evaluated else 0,
        "p95_latency_ms": _p95(latencies),
        "notes": [
            "Offline evaluation disables external map verification and verifies only approved local facts.",
            "allowed_poi_ids defaults to the test sample fact pack. Export complete fact-pack IDs for a broader candidate-violation measurement.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fixed TripCraft test samples")
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = evaluate_samples(_read_jsonl(args.test), _read_jsonl(args.predictions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
