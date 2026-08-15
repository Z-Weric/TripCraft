"""Convert approved TripCraft split JSONL into LLaMA-Factory SFT data.

The model is trained only to produce the allow-listed narrative. The planner owns
all POI, route, schedule, coordinate, duration, and cost facts at runtime.
"""

import argparse
import json
from pathlib import Path
from typing import Any


SYSTEM_INSTRUCTION = """You write TripCraft itinerary narrative from a planner fact pack.
Return one JSON object only. You may only write summary, transport_advice, note, and reason.
Copy every day and poi_id exactly as supplied. Do not output POI names, coordinates, costs,
durations, route ordering, or fields outside this schema:
{"summary":"string","days":[{"day":1,"transport_advice":"string","items":[{"poi_id":1,"note":"string","reason":"string"}]}]}"""


def _as_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _itinerary(sample: dict[str, Any]) -> dict[str, Any]:
    for field in ("expected_itinerary", "itinerary", "output"):
        itinerary = _as_object(sample.get(field))
        if isinstance(itinerary.get("itinerary"), list):
            return itinerary
    return {}


def _request(sample: dict[str, Any], itinerary: dict[str, Any]) -> dict[str, Any]:
    request = sample.get("request")
    if not isinstance(request, dict):
        request = _as_object(sample.get("instruction"))
    return {
        "destination": str(request.get("destination") or itinerary.get("destination") or "").strip(),
        "days": request.get("days") or itinerary.get("days"),
        "budget": request.get("budget") or itinerary.get("budget"),
        "preferences": request.get("preferences") if isinstance(request.get("preferences"), list) else [],
    }


def build_training_record(sample: dict[str, Any]) -> dict[str, str] | None:
    """Build an Alpaca record with immutable facts in the instruction and prose in output."""
    itinerary = _itinerary(sample)
    request = _request(sample, itinerary)
    if not request["destination"] or not isinstance(itinerary.get("itinerary"), list):
        return None

    fact_days: list[dict[str, Any]] = []
    narrative_days: list[dict[str, Any]] = []
    for day in itinerary["itinerary"]:
        if not isinstance(day, dict) or not isinstance(day.get("day"), int) or not isinstance(day.get("items"), list):
            return None
        fact_items: list[dict[str, Any]] = []
        narrative_items: list[dict[str, Any]] = []
        for item in day["items"]:
            if not isinstance(item, dict) or not isinstance(item.get("poi_id"), int):
                return None
            fact_items.append(
                {
                    key: item[key]
                    for key in (
                        "poi_id", "spot", "category", "time", "lat", "lng", "cost", "duration",
                        "distance_from_previous_km", "transport_cost", "recommendation_labels",
                    )
                    if key in item
                }
            )
            narrative_items.append(
                {
                    "poi_id": item["poi_id"],
                    "note": str(item.get("note") or ""),
                    "reason": str(item.get("reason") or ""),
                }
            )
        fact_days.append(
            {
                "day": day["day"],
                "day_cost": day.get("day_cost"),
                "items": fact_items,
            }
        )
        narrative_days.append(
            {
                "day": day["day"],
                "transport_advice": str(day.get("transport_advice") or ""),
                "items": narrative_items,
            }
        )

    fact_pack = {
        **request,
        "total_cost": itinerary.get("total_cost"),
        "itinerary": fact_days,
    }
    narrative = {"summary": str(itinerary.get("summary") or ""), "days": narrative_days}
    fact_pack_json = json.dumps(fact_pack, ensure_ascii=False, separators=(",", ":"))
    return {
        "instruction": f"{SYSTEM_INSTRUCTION}\n\nFact pack:\n{fact_pack_json}",
        "input": "",
        "output": json.dumps(narrative, ensure_ascii=False, separators=(",", ":")),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, records: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare allow-listed TripCraft SFT data")
    parser.add_argument("--input", type=Path, required=True, help="Train split JSONL from build_dataset.py")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality-labels", default="gold", help="Comma-separated permitted labels; default gold")
    args = parser.parse_args()

    allowed_labels = {label.strip() for label in args.quality_labels.split(",") if label.strip()}
    records: list[dict[str, str]] = []
    skipped: list[str] = []
    for index, sample in enumerate(_read_jsonl(args.input), start=1):
        if str(sample.get("quality_label")) not in allowed_labels:
            continue
        record = build_training_record(sample)
        if record is None:
            skipped.append(str(sample.get("id") or f"line-{index}"))
        else:
            records.append(record)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(args.output, records)
    print(json.dumps({"records": len(records), "skipped_sample_ids": skipped}, ensure_ascii=False))


if __name__ == "__main__":
    main()
