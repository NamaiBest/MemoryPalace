"""Reduced-electrode experiments. Channel sets are defined in config.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.evaluate import evaluate_npz, summarize_folds  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402
from src.train_classifier import run as train_run  # noqa: E402


def run(model: str = "logreg") -> dict:
    """Train LOSO for each channel set. Default model is logistic regression
    so the ablation is comparable and fast. RF is also trained for all16 in
    the main train step.
    """
    log = setup_logging("ablation")
    ensure_dirs()
    table = {}
    for name, chans in C.CHANNEL_SETS.items():
        log.info("channel set %s (%s)", name, chans)
        train_run("features_event", name, models=(model,))
        pred_path = C.CACHE_DIR / f"pred_features_event_{name}_{model}.npz"
        ev = evaluate_npz(pred_path)
        loso = ev["loso_mean_std"]
        table[name] = {
            "channels": chans,
            "n_channels": len(chans),
            "note": C.CHANNEL_SET_NOTES[name],
            "balanced_accuracy_mean": loso["balanced_accuracy"]["mean"],
            "balanced_accuracy_std": loso["balanced_accuracy"]["std"],
            "roc_auc_mean": loso["roc_auc"]["mean"] if loso["roc_auc"] else None,
            "recall_mean": loso["recall"]["mean"],
            "specificity_mean": loso["specificity"]["mean"],
            "fpr_mean": loso["fpr"]["mean"],
            "pooled": ev["pooled"],
        }
    write_json(C.RESULTS_DIR / "electrode_ablation.json", table)
    log.info("wrote electrode_ablation.json")
    return table


def main() -> None:
    run()


if __name__ == "__main__":
    main()
