"""Export explicitly approved automatic candidates into the existing SFT split pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingScenario


def build_auto_sft_sample(label: Any, run: Any, scenario: Any) -> dict[str, Any]:
    """Build the same sanitized format as existing SFT exports, without reviewer/user identities."""
    response = json.loads(run.response_json)
    itinerary = response.get("itinerary", {})
    request = json.loads(scenario.request_json)
    return {
        "id": f"auto-run-{run.id}",
        "instruction": json.dumps(request, ensure_ascii=False),
        "output": json.dumps(itinerary, ensure_ascii=False),
        "metadata": {
            "source": "approved_auto_label",
            "approval_batch": label.approval_batch,
            "auto_label_id": label.id,
            "confidence": label.confidence,
            "rule_version": label.rule_version,
            "generation_source": run.generation_source,
            "validation_status": run.validation_status,
            "model_version": run.generator_model,
            "matrix_version": scenario.matrix_version,
        },
        "quality_label": "gold",
    }


def export_batch(batch: str, output: Path) -> int:
    db = SessionLocal()
    try:
        rows = (
            db.query(TrainingAutoLabel, TrainingGenerationRun, TrainingScenario)
            .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
            .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
            .filter(
                TrainingAutoLabel.approval_status == "approved",
                TrainingAutoLabel.approval_batch == batch,
                TrainingAutoLabel.label == "auto_gold_candidate",
                TrainingScenario.scenario_type == "matrix",
            )
            .order_by(TrainingAutoLabel.id)
            .all()
        )
        samples = [build_auto_sft_sample(label, run, scenario) for label, run, scenario in rows]
    finally:
        db.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return len(samples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export one approved automatic-label batch for SFT splitting")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export_batch(args.batch, args.output)
    print(json.dumps({"batch": args.batch, "samples": count, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
