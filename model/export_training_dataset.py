"""训练样本导出脚本 — 从已保存行程导出脱敏训练数据

从 SavedTrip 和 TripQualityLog 导出可供 SFT/评测使用的训练样本。
所有导出数据均经过脱敏：移除 user_id、邮箱等可识别个人信息。

用法:
    cd TripCraft
    python model/export_training_dataset.py [--output training_data/exported] [--min-rating 3] [--format sft]

参数:
    --output      输出目录（默认 model/training_data/exported）
    --min-rating  最低用户评分门槛（默认 3，即 >=3 视为正样本）
    --format      输出格式：sft | eval | all（默认 all）
    --limit       最多导出条数（默认不限）
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database.models import SessionLocal, SavedTrip, TripQualityLog
from utils.logger import logger


def _sanitize_itinerary(itinerary: dict[str, Any]) -> dict[str, Any]:
    """Remove user-identifiable fields from itinerary; keep POI facts only."""
    cleaned = {k: v for k, v in itinerary.items() if k != "planning_warnings"}
    return cleaned


def _sanitize_verification(verification: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep validation structure; drop nothing sensitive (verification has no PII)."""
    if verification is None:
        return None
    return verification


def _build_sft_sample(trip: SavedTrip) -> dict[str, Any]:
    """Build a single SFT instruction-output pair from a saved trip."""
    itinerary = json.loads(trip.itinerary_json)
    verification = json.loads(trip.verification_json) if trip.verification_json else None

    preferences = trip.preferences.split(",") if trip.preferences else []

    instruction = {
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "preferences": preferences,
    }

    return {
        "id": f"trip-{trip.id}",
        "instruction": json.dumps(instruction, ensure_ascii=False),
        "output": json.dumps(_sanitize_itinerary(itinerary), ensure_ascii=False),
        "metadata": {
            "generation_source": trip.generation_source,
            "validation_status": trip.validation_status,
            "model_version": trip.model_version,
            "user_rating": trip.user_rating,
            "poi_version": trip.poi_version,
            "planner_version": trip.planner_version,
            "exported_at": datetime.utcnow().isoformat() + "Z",
        },
        "quality_label": _quality_label(trip),
    }


def _build_eval_sample(trip: SavedTrip) -> dict[str, Any]:
    """Build an evaluation sample: input + expected structure + validation result."""
    itinerary = json.loads(trip.itinerary_json)
    verification = json.loads(trip.verification_json) if trip.verification_json else None
    preferences = trip.preferences.split(",") if trip.preferences else []

    return {
        "id": f"trip-{trip.id}",
        "request": {
            "destination": trip.destination,
            "days": trip.days,
            "budget": trip.budget,
            "preferences": preferences,
        },
        "expected_itinerary": _sanitize_itinerary(itinerary),
        "verification": _sanitize_verification(verification),
        "metadata": {
            "generation_source": trip.generation_source,
            "validation_status": trip.validation_status,
            "model_version": trip.model_version,
            "user_rating": trip.user_rating,
            "poi_version": trip.poi_version,
        },
        "quality_label": _quality_label(trip),
    }


def _quality_label(trip: SavedTrip) -> str:
    """Assign a quality label based on rating, validation status, and generation source."""
    if trip.user_rating >= 4 and trip.validation_status == "valid":
        return "gold"
    if trip.user_rating >= 3 and trip.validation_status in ("valid", "repaired"):
        return "silver"
    if trip.validation_status == "fallback":
        return "fallback"
    if trip.user_rating <= 2:
        return "negative"
    return "unlabeled"


def _build_negative_sample(log: TripQualityLog) -> dict[str, Any]:
    """Build a negative/repair sample from a quality log entry."""
    reason = json.loads(log.reason_json)
    return {
        "id": f"quality-log-{log.id}",
        "trigger": log.trigger,
        "destination": log.destination,
        "days": log.days,
        "budget": log.budget,
        "error_codes": reason.get("error_codes", []),
        "fallback_reason": log.fallback_reason,
        "generation_source": log.generation_source,
        "validation_status": log.validation_status,
        "model_version": log.model_version,
        "quality_label": "negative",
    }


def export_sft(db, output_dir: str, min_rating: int, limit: int | None = None) -> int:
    """Export SFT samples: positive (rating >= min_rating) + negative (quality logs)."""
    samples = []
    query = db.query(SavedTrip).filter(SavedTrip.user_rating >= min_rating).order_by(SavedTrip.created_at)
    if limit:
        query = query.limit(limit)

    for trip in query:
        samples.append(_build_sft_sample(trip))

    gold = sum(1 for s in samples if s["quality_label"] == "gold")
    silver = sum(1 for s in samples if s["quality_label"] == "silver")

    path = os.path.join(output_dir, "sft_samples.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    logger.info(f"SFT 导出: {len(samples)} 条 (gold={gold}, silver={silver}) -> {path}")
    return len(samples)


def export_eval(db, output_dir: str, min_rating: int, limit: int | None = None) -> int:
    """Export evaluation samples with full verification context."""
    samples = []
    query = db.query(SavedTrip).filter(SavedTrip.user_rating >= min_rating).order_by(SavedTrip.created_at)
    if limit:
        query = query.limit(limit)

    for trip in query:
        samples.append(_build_eval_sample(trip))

    path = os.path.join(output_dir, "eval_samples.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    logger.info(f"评测集导出: {len(samples)} 条 -> {path}")
    return len(samples)


def export_negatives(db, output_dir: str, limit: int | None = None) -> int:
    """Export negative/repair samples from quality logs."""
    samples = []
    query = db.query(TripQualityLog).order_by(TripQualityLog.created_at)
    if limit:
        query = query.limit(limit)

    for log in query:
        samples.append(_build_negative_sample(log))

    path = os.path.join(output_dir, "negative_samples.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    logger.info(f"负样本导出: {len(samples)} 条 -> {path}")
    return len(samples)


def main():
    parser = argparse.ArgumentParser(description="导出脱敏训练样本")
    parser.add_argument("--output", default=os.path.join(os.path.dirname(__file__), "training_data", "exported"))
    parser.add_argument("--min-rating", type=int, default=3, help="正样本最低评分门槛")
    parser.add_argument("--format", choices=["sft", "eval", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None, help="每种最多导出条数")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    db = SessionLocal()

    total = 0
    if args.format in ("sft", "all"):
        total += export_sft(db, args.output, args.min_rating, args.limit)
    if args.format in ("eval", "all"):
        total += export_eval(db, args.output, args.min_rating, args.limit)
    if args.format == "all":
        total += export_negatives(db, args.output, args.limit)

    # 导出 manifest
    manifest = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "min_rating": args.min_rating,
        "format": args.format,
        "limit": args.limit,
        "total_samples": total,
        "note": "所有数据已脱敏，不含 user_id、邮箱等 PII。禁止直接用于在线训练。",
    }
    manifest_path = os.path.join(args.output, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    db.close()
    print(f"导出完成: {total} 条样本 -> {args.output}")


if __name__ == "__main__":
    main()
