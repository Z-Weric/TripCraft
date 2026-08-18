"""Export a read-only, de-identified review queue for silver auto-labels."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database.models import SessionLocal, TrainingAutoLabel, TrainingEvidence, TrainingGenerationRun, TrainingScenario
from services.training_judge_service import fact_pack_from_itinerary, narrative_from_itinerary


def build_review_packet(label: Any, run: Any, scenario: Any, evidence: list[Any]) -> dict[str, Any]:
    """Keep only synthetic request, planner output, audit judgments, and public citations."""
    request = json.loads(scenario.request_json)
    response = json.loads(run.response_json)
    itinerary = response.get("itinerary") if isinstance(response.get("itinerary"), dict) else {}
    return {
        "run_id": run.id,
        "label": label.label,
        "confidence": label.confidence,
        "request": request,
        "fact_pack": fact_pack_from_itinerary(request, itinerary),
        "narrative": narrative_from_itinerary(itinerary),
        "verification": response.get("verification"),
        "decision": json.loads(label.decision_json),
        "evidence": [
            {
                "claim": item.claim_text,
                "query": item.query_text,
                "sources": json.loads(item.sources_json),
                "retrieval_error": item.retrieval_error,
            }
            for item in evidence
        ],
    }


def export_queue(output: Path, min_confidence: float, limit: int | None = None) -> int:
    db = SessionLocal()
    try:
        query = (
            db.query(TrainingAutoLabel, TrainingGenerationRun, TrainingScenario)
            .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
            .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
            .filter(
                TrainingAutoLabel.label == "silver",
                TrainingAutoLabel.approval_status == "pending",
                TrainingAutoLabel.confidence >= min_confidence,
                TrainingScenario.scenario_type == "matrix",
            )
            .order_by(TrainingAutoLabel.confidence.desc(), TrainingAutoLabel.id)
        )
        rows = query.limit(limit).all() if limit else query.all()
        packets = [
            build_review_packet(
                label,
                run,
                scenario,
                db.query(TrainingEvidence).filter(TrainingEvidence.run_id == run.id).all(),
            )
            for label, run, scenario in rows
        ]
    finally:
        db.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for packet in packets:
            handle.write(json.dumps(packet, ensure_ascii=False) + "\n")
    return len(packets)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export pending silver samples for manual review")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-confidence", type=float, default=0.85)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not 0 <= args.min_confidence <= 1:
        raise SystemExit("--min-confidence must be between 0 and 1")
    count = export_queue(args.output, args.min_confidence, args.limit)
    print(json.dumps({"queued": count, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
