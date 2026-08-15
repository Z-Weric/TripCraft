"""Generate a deterministic, quota-friendly matrix of TripCraft API requests."""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any


MATRIX_VERSION = "benchmark-matrix-v1"
DEFAULT_DAYS = (1, 2, 3, 5)
DEFAULT_PREFERENCE_GROUPS = (("自然风光",), ("美食",), ("人文历史",), ("亲子",), ("自然风光", "美食"))


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _budgets(days: int) -> tuple[int, int, int]:
    return (max(200, days * 250), days * 600, days * 1200)


def build_cases(cities: list[str], max_cases: int, seed: int, include_challenges: bool = False, challenges: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for city in sorted(set(cities)):
        for days in DEFAULT_DAYS:
            for budget_tier, budget in zip(("compact", "standard", "generous"), _budgets(days)):
                for preferences in DEFAULT_PREFERENCE_GROUPS:
                    request = {"destination": city, "days": days, "budget": budget, "preferences": list(preferences)}
                    candidates.append(
                        {
                            "scenario_id": _hash({"version": MATRIX_VERSION, "request": request})[:24],
                            "request": request,
                            "bucket": {"city": city, "days": days, "budget_tier": budget_tier, "preferences": list(preferences)},
                            "expected_risks": [],
                            "matrix_version": MATRIX_VERSION,
                            "scenario_type": "matrix",
                            "seed": seed,
                        }
                    )
    random.Random(seed).shuffle(candidates)
    selected = candidates[:max_cases]
    if include_challenges:
        for challenge in challenges or []:
            request = challenge["request"]
            selected.append(
                {
                    "scenario_id": challenge["id"],
                    "request": request,
                    "bucket": challenge.get("bucket", {"type": "challenge"}),
                    "expected_risks": challenge.get("expected_risks", []),
                    "matrix_version": MATRIX_VERSION,
                    "scenario_type": "challenge",
                    "seed": seed,
                }
            )
    return selected


def _load_challenges(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _db_cities(min_pois: int) -> list[str]:
    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    from database.models import POI, SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(POI.city).group_by(POI.city).having(__import__("sqlalchemy").func.count(POI.id) >= min_pois).all()
        return [city for (city,) in rows if city and city != "??"]
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reproducible TripCraft benchmark cases")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cities", default="", help="Comma-separated cities; defaults to database cities with sufficient POIs")
    parser.add_argument("--min-pois", type=int, default=20)
    parser.add_argument("--max-cases", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument("--include-challenges", action="store_true")
    parser.add_argument("--challenges", type=Path, default=Path(__file__).with_name("challenge_cases.jsonl"))
    args = parser.parse_args()

    cities = [item.strip() for item in args.cities.split(",") if item.strip()] or _db_cities(args.min_pois)
    cases = build_cases(cities, args.max_cases, args.seed, args.include_challenges, _load_challenges(args.challenges) if args.include_challenges else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for item in cases:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(json.dumps({"matrix_version": MATRIX_VERSION, "cases": len(cases), "cities": cities, "seed": args.seed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
