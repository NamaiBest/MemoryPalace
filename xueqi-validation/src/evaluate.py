"""Metrics for LOSO predictions. Never used to pick features."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402


def metrics_block(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray) -> dict:
    y_true = y_true.astype(int)
    y_pred = y_pred.astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    fpr = fp / (tn + fp) if (tn + fp) else 0.0
    out = {
        "n": int(len(y_true)),
        "n_positive": int(y_true.sum()),
        "n_negative": int((y_true == 0).sum()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(spec),
        "fpr": float(fpr),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    if len(np.unique(y_true)) > 1:
        out["roc_auc"] = float(roc_auc_score(y_true, y_score))
    else:
        out["roc_auc"] = None
    return out


def per_subject(y_true, y_pred, y_score, subjects) -> list[dict]:
    rows = []
    for s in sorted(np.unique(subjects)):
        m = subjects == s
        block = metrics_block(y_true[m], y_pred[m], y_score[m])
        block["subject"] = str(s)
        rows.append(block)
    return rows


def summarize_folds(rows: list[dict]) -> dict:
    keys = [
        "accuracy",
        "balanced_accuracy",
        "precision",
        "recall",
        "specificity",
        "fpr",
        "f1",
        "roc_auc",
    ]
    out = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        if not vals:
            out[k] = None
            continue
        out[k] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals, ddof=1) if len(vals) > 1 else 0.0),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
        }
    return out


def evaluate_npz(path: Path) -> dict:
    z = np.load(path, allow_pickle=False)
    y_true, y_pred, y_score = z["y_true"], z["y_pred"], z["y_score"]
    subj = z["subject"].astype(str)
    pooled = metrics_block(y_true, y_pred, y_score)
    folds = per_subject(y_true, y_pred, y_score, subj)
    return {
        "pooled": pooled,
        "per_subject": folds,
        "loso_mean_std": summarize_folds(folds),
        "n_subjects": len(folds),
        "chance_balanced_accuracy": 0.5,
    }


def evaluate_all() -> dict:
    log = setup_logging("evaluate")
    ensure_dirs()
    results = {}
    for path in sorted(C.CACHE_DIR.glob("pred_*.npz")):
        key = path.stem.replace("pred_", "")
        log.info("evaluate %s", key)
        results[key] = evaluate_npz(path)
    write_json(C.RESULTS_DIR / "classification.json", results)
    return results


def main() -> None:
    evaluate_all()


if __name__ == "__main__":
    main()
