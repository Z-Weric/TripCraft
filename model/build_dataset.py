"""Build deterministic, leak-resistant train/validation/test splits from JSONL exports."""

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


QUALITY_RANK = {"gold": 4, "silver": 3, "fallback": 2, "unlabeled": 1, "negative": 0}
SPLIT_NAMES = ("train", "validation", "test")


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def request_payload(sample: dict[str, Any]) -> dict[str, Any]:
    request = sample.get("request")
    if not isinstance(request, dict):
        request = _parse_payload(sample.get("instruction"))
    return {
        "destination": str(request.get("destination", "")).strip(),
        "days": request.get("days"),
        "budget": request.get("budget"),
        "preferences": sorted(
            str(item).strip() for item in request.get("preferences", []) if str(item).strip()
        ),
    }


def itinerary_payload(sample: dict[str, Any]) -> dict[str, Any]:
    for field in ("expected_itinerary", "itinerary", "output"):
        itinerary = _parse_payload(sample.get(field))
        if itinerary:
            return itinerary
    return {}


def poi_sequence(sample: dict[str, Any]) -> list[str]:
    sequence: list[str] = []
    for day in itinerary_payload(sample).get("itinerary", []):
        if not isinstance(day, dict):
            continue
        for item in day.get("items", []):
            if not isinstance(item, dict):
                continue
            poi_id = item.get("poi_id")
            if isinstance(poi_id, int) and poi_id > 0:
                sequence.append(f"id:{poi_id}")
            elif isinstance(item.get("spot"), str) and item["spot"].strip():
                sequence.append(f"name:{item['spot'].strip()}")
    return sequence


@dataclass(frozen=True)
class PreparedSample:
    sample: dict[str, Any]
    sample_id: str
    request_key: str
    poi_key: str
    quality_rank: int


def prepare_samples(samples: Iterable[dict[str, Any]]) -> tuple[list[PreparedSample], list[str]]:
    prepared: list[PreparedSample] = []
    skipped: list[str] = []
    for index, sample in enumerate(samples):
        sample_id = str(sample.get("id") or f"line-{index + 1}")
        request = request_payload(sample)
        sequence = poi_sequence(sample)
        if not request["destination"] or not sequence:
            skipped.append(sample_id)
            continue
        prepared.append(
            PreparedSample(
                sample=sample,
                sample_id=sample_id,
                request_key=_canonical_hash(request),
                poi_key=_canonical_hash(sequence),
                quality_rank=QUALITY_RANK.get(str(sample.get("quality_label", "unlabeled")), 1),
            )
        )
    return prepared, skipped


def deduplicate_samples(samples: list[PreparedSample]) -> tuple[list[PreparedSample], dict[str, list[str]]]:
    """Keep one highest-quality representative for every request/POI collision group."""
    parents = list(range(len(samples)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    seen_request: dict[str, int] = {}
    seen_poi: dict[str, int] = {}
    for index, sample in enumerate(samples):
        for key, seen in ((sample.request_key, seen_request), (sample.poi_key, seen_poi)):
            if key in seen:
                union(index, seen[key])
            else:
                seen[key] = index

    groups: dict[int, list[PreparedSample]] = defaultdict(list)
    for index, sample in enumerate(samples):
        groups[find(index)].append(sample)

    retained: list[PreparedSample] = []
    dropped: dict[str, list[str]] = {}
    for group in groups.values():
        ordered = sorted(group, key=lambda item: (-item.quality_rank, item.sample_id))
        retained.append(ordered[0])
        if len(ordered) > 1:
            dropped[ordered[0].sample_id] = [item.sample_id for item in ordered[1:]]
    return sorted(retained, key=lambda item: item.sample_id), dropped


def _split_counts(total: int, ratios: tuple[float, float, float]) -> dict[str, int]:
    raw = [total * ratio for ratio in ratios]
    counts = [int(value) for value in raw]
    for index in sorted(range(3), key=lambda item: (raw[item] - counts[item], -item), reverse=True)[: total - sum(counts)]:
        counts[index] += 1
    return dict(zip(SPLIT_NAMES, counts))


def split_samples(samples: list[PreparedSample], ratios: tuple[float, float, float]) -> dict[str, list[dict[str, Any]]]:
    counts = _split_counts(len(samples), ratios)
    ordered = sorted(samples, key=lambda item: _canonical_hash(item.sample_id))
    result: dict[str, list[dict[str, Any]]] = {}
    cursor = 0
    for name in SPLIT_NAMES:
        next_cursor = cursor + counts[name]
        result[name] = [item.sample for item in ordered[cursor:next_cursor]]
        cursor = next_cursor
    return result


def build_dataset(samples: list[dict[str, Any]], ratios: tuple[float, float, float]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    prepared, skipped = prepare_samples(samples)
    retained, dropped = deduplicate_samples(prepared)
    splits = split_samples(retained, ratios)
    manifest = {
        "input_samples": len(samples),
        "eligible_samples": len(prepared),
        "retained_samples": len(retained),
        "skipped_sample_ids": skipped,
        "deduplicated_sample_ids": dropped,
        "split_counts": {name: len(items) for name, items in splits.items()},
        "ratios": dict(zip(SPLIT_NAMES, ratios)),
        "deduplication": "Samples sharing a normalized request or ordered POI sequence are kept as one highest-quality representative.",
    }
    return splits, manifest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number} must be a JSON object")
            samples.append(value)
    return samples


def _write_jsonl(path: Path, samples: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build leak-resistant train/validation/test JSONL splits")
    parser.add_argument("--input", type=Path, required=True, help="JSONL exported by export_training_dataset.py")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ratios", default="0.8,0.1,0.1", help="train,validation,test ratios")
    args = parser.parse_args()

    ratios = tuple(float(value) for value in args.ratios.split(","))
    if len(ratios) != 3 or any(value <= 0 for value in ratios) or abs(sum(ratios) - 1) > 1e-9:
        raise ValueError("--ratios must contain three positive values that sum to 1")

    splits, manifest = build_dataset(_read_jsonl(args.input), ratios)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, samples in splits.items():
        _write_jsonl(args.output / f"{name}.jsonl", samples)
    with (args.output / "split_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(json.dumps(manifest["split_counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
