#!/usr/bin/env python3
"""Run the full MemoryPalace surprise-EEG pipeline.

Usage (from this folder, with the project venv):

    python src/inspect_dataset.py
    python src/run_all.py

Flags:
    --force           recompute cached epochs
    --skip-trigger    skip the slower continuous-stream stage
    --skip-figures
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="MemoryPalace surprise-EEG pipeline")
    p.add_argument("--force", action="store_true")
    p.add_argument("--skip-trigger", action="store_true")
    p.add_argument("--skip-figures", action="store_true")
    args = p.parse_args()

    ensure_dirs()
    log = setup_logging("run_all")
    log.info("PROJECT_ROOT=%s", C.PROJECT_ROOT)
    log.info("DATASET_ROOT=%s", C.DATASET_ROOT)

    from src.inspect_dataset import main as inspect_main
    from src.extract_events import main as events_main
    from src.preprocess import run as preprocess_run
    from src.event_analysis import run as analysis_run
    from src.extract_features import run as features_run
    from src.train_classifier import loso_predict, run as train_run
    from src.evaluate import evaluate_all
    from src.electrode_ablation import run as ablation_run
    from src.extract_features import load_table
    from src.io_utils import write_json
    import numpy as np

    log.info("=== inspect ===")
    inspect_main()
    log.info("=== events ===")
    events_main()
    log.info("=== preprocess / epoch ===")
    preprocess_run(force=args.force)
    log.info("=== event-related analysis ===")
    analysis_run()
    log.info("=== features ===")
    features_run()
    log.info("=== train all16 models ===")
    train_run("features_event", "all16")
    log.info("=== negative control: shuffled train labels ===")
    table = load_table("features_event")
    shuf = loso_predict(table["X"], table["y"], table["subject"], "logreg", shuffle_train_labels=True)
    np.savez_compressed(
        C.CACHE_DIR / "pred_features_event_all16_logreg_shuffled.npz",
        y_true=shuf["y_true"],
        y_pred=shuf["y_pred"],
        y_score=shuf["y_score"],
        subject=shuf["subject"],
    )
    log.info("=== negative control: pre-event features ===")
    train_run("features_preevent", "all16", models=("logreg",))
    log.info("=== evaluate ===")
    evaluate_all()
    log.info("=== electrode ablation ===")
    ablation_run("logreg")
    if not args.skip_trigger:
        log.info("=== continuous trigger ===")
        from src.continuous_trigger import run as trigger_run

        trigger_run(force_windows=args.force)
    if not args.skip_figures:
        log.info("=== figures ===")
        from src.make_figures import run as figures_run

        figures_run()
    log.info("done. See results/ and figures/")
    write_json(C.RESULTS_DIR / "run_complete.json", {"ok": True, "seed": C.RANDOM_SEED})


if __name__ == "__main__":
    main()
