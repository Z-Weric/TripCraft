"""Threshold-triggered background repair for pending silver candidates."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODEL_DIR = ROOT / "model"
TRAINING_DIR = MODEL_DIR / "training_data"
LOCK_PATH = TRAINING_DIR / ".silver_repair_trigger.lock"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database.models import SessionLocal, TrainingAutoLabel, TrainingGenerationRun, TrainingScenario


def count_unrepaired_pending_silver(db) -> int:
    """Count source silver labels that do not yet have a repair child."""
    rows = (
        db.query(TrainingAutoLabel.run_id)
        .join(TrainingGenerationRun, TrainingGenerationRun.id == TrainingAutoLabel.run_id)
        .join(TrainingScenario, TrainingScenario.id == TrainingGenerationRun.scenario_id)
        .filter(
            TrainingAutoLabel.label == "silver",
            TrainingAutoLabel.approval_status == "pending",
            TrainingScenario.scenario_type == "matrix",
            (TrainingGenerationRun.repair_iteration == 0) | (TrainingGenerationRun.repair_iteration.is_(None)),
        )
        .all()
    )
    source_ids = {run_id for (run_id,) in rows}
    if not source_ids:
        return 0
    child_parent_ids = {
        parent_id
        for (parent_id,) in db.query(TrainingGenerationRun.parent_run_id)
        .filter(TrainingGenerationRun.parent_run_id.in_(source_ids))
        .all()
        if parent_id is not None
    }
    return len(source_ids - child_parent_ids)


def _lock_is_active() -> bool:
    if not LOCK_PATH.exists():
        return False
    try:
        age = datetime.now(timezone.utc).timestamp() - LOCK_PATH.stat().st_mtime
        return age < 6 * 60 * 60
    except OSError:
        return False


def _acquire_lock() -> bool:
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with LOCK_PATH.open("x", encoding="ascii") as handle:
            handle.write(f"pid={os.getpid()}\n")
        return True
    except FileExistsError:
        return False


def _release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def trigger_if_needed(*, dry_run: bool = False) -> dict[str, object]:
    if not settings.auto_eval_enabled or not settings.auto_eval_repair_enabled or not settings.auto_eval_repair_trigger_enabled:
        return {"triggered": False, "reason": "disabled"}
    db = SessionLocal()
    try:
        pending = count_unrepaired_pending_silver(db)
    finally:
        db.close()
    threshold = settings.auto_eval_repair_trigger_threshold
    if pending < threshold:
        return {"triggered": False, "reason": "below_threshold", "pending": pending, "threshold": threshold}
    if _lock_is_active() or not _acquire_lock():
        return {"triggered": False, "reason": "already_running", "pending": pending}
    if dry_run:
        _release_lock()
        return {"triggered": False, "reason": "dry_run", "pending": pending, "threshold": threshold}

    batch = f"auto-trigger-repair-{datetime.now():%Y%m%d-%H%M%S}"
    output = TRAINING_DIR / f"{batch}.jsonl"
    log_path = TRAINING_DIR / f"{batch}.log"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--repair-output",
        str(output),
        "--repair-batch",
        batch,
        "--repair-limit",
        str(settings.auto_eval_repair_trigger_batch_size),
        "--repair-max-iterations",
        str(settings.auto_eval_repair_max_iterations),
    ]
    log_path = TRAINING_DIR / f"{batch}.log"
    try:
        log_handle = log_path.open("a", encoding="utf-8")
        kwargs = {"cwd": str(ROOT), "stdout": log_handle, "stderr": subprocess.STDOUT}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        subprocess.Popen(command, **kwargs)
    except Exception:
        _release_lock()
        raise
    return {"triggered": True, "pending": pending, "threshold": threshold, "batch": batch, "output": str(output)}


def _run_worker(output: Path, batch: str, limit: int, max_iterations: int) -> None:
    command = [
        sys.executable,
        str(MODEL_DIR / "repair_silver_training_samples.py"),
        "--output",
        str(output),
        "--limit",
        str(limit),
        "--max-iterations",
        str(max_iterations),
        "--approval-batch",
        batch,
        "--only-unrepaired",
    ]
    log_path = TRAINING_DIR / f"{batch}.log"
    try:
        log_handle = log_path.open("a", encoding="utf-8")
        try:
            subprocess.run(command, cwd=str(ROOT), stdout=log_handle, stderr=subprocess.STDOUT, check=False)
        finally:
            log_handle.close()
    finally:
        _release_lock()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start silver repair when the unrepaired threshold is reached")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--repair-output", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--repair-batch", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--repair-limit", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--repair-max-iterations", type=int, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if not args.repair_output or not args.repair_batch or not args.repair_limit or not args.repair_max_iterations:
            raise SystemExit("worker arguments are incomplete")
        _run_worker(args.repair_output, args.repair_batch, args.repair_limit, args.repair_max_iterations)
        return
    print(json.dumps(trigger_if_needed(dry_run=args.dry_run), ensure_ascii=False))


if __name__ == "__main__":
    main()
