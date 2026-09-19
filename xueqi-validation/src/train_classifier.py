"""Leave-one-subject-out classifiers. Train-fold only scaling and fitting."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.extract_features import columns_for_channels, load_table  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402


def set_seed(seed: int = C.RANDOM_SEED) -> None:
    np.random.seed(seed)


def make_model(name: str, seed: int = C.RANDOM_SEED):
    if name == "majority":
        return "majority"
    if name == "logreg":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        C=1.0,
                        random_state=seed,
                    ),
                ),
            ]
        )
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        )
    if name == "hgb":
        # sklearn HGB has no class_weight until recent versions; use sample_weight.
        return HistGradientBoostingClassifier(
            max_depth=6,
            learning_rate=0.08,
            max_iter=150,
            random_state=seed,
        )
    raise ValueError(name)


def _sample_weight(y: np.ndarray) -> np.ndarray:
    n0 = max(int((y == 0).sum()), 1)
    n1 = max(int((y == 1).sum()), 1)
    w = np.ones(len(y), dtype=np.float64)
    w[y == 0] = 0.5 * len(y) / n0
    w[y == 1] = 0.5 * len(y) / n1
    return w


def loso_predict(
    X: np.ndarray,
    y: np.ndarray,
    subjects: np.ndarray,
    model_name: str,
    shuffle_train_labels: bool = False,
    seed: int = C.RANDOM_SEED,
) -> dict:
    """Return out-of-subject scores and predictions."""
    set_seed(seed)
    rng = np.random.default_rng(seed)
    uniq = np.array(sorted(np.unique(subjects)))
    y_true = np.zeros(len(y), dtype=np.int8)
    y_pred = np.zeros(len(y), dtype=np.int8)
    y_score = np.zeros(len(y), dtype=np.float64)
    fold_subjects = np.empty(len(y), dtype=object)
    for held in uniq:
        tr = subjects != held
        te = subjects == held
        Xtr, ytr = X[tr], y[tr].astype(int)
        Xte, yte = X[te], y[te].astype(int)
        if shuffle_train_labels:
            ytr = rng.permutation(ytr)
        model = make_model(model_name, seed)
        if model == "majority":
            maj = int(np.bincount(ytr).argmax()) if len(ytr) else 0
            pred = np.full(len(yte), maj, dtype=np.int8)
            # majority has no ranking; use class prior
            prior = float(ytr.mean()) if len(ytr) else 0.0
            score = np.full(len(yte), prior, dtype=np.float64)
        else:
            sw = _sample_weight(ytr)
            if model_name == "hgb":
                model.fit(Xtr, ytr, sample_weight=sw)
            elif model_name == "rf":
                model.fit(Xtr, ytr)
            else:
                model.fit(Xtr, ytr)
            pred = model.predict(Xte).astype(np.int8)
            if hasattr(model, "predict_proba"):
                score = model.predict_proba(Xte)[:, 1]
            else:
                score = model.decision_function(Xte)
                score = 1.0 / (1.0 + np.exp(-score))
        y_true[te] = yte
        y_pred[te] = pred
        y_score[te] = score
        fold_subjects[te] = held
    return {
        "y_true": y_true,
        "y_pred": y_pred,
        "y_score": y_score,
        "subject": fold_subjects.astype(str),
        "held_out_subjects": uniq.tolist(),
        "model": model_name,
        "shuffle_train_labels": shuffle_train_labels,
    }


def run(
    table_name: str = "features_event",
    channel_set: str = "all16",
    models: tuple[str, ...] = ("majority", "logreg", "rf", "hgb"),
) -> dict:
    log = setup_logging("train")
    ensure_dirs()
    table = load_table(table_name)
    keep = C.CHANNEL_SETS[channel_set]
    cols = columns_for_channels(table["feature_names"].tolist(), keep)
    X = table["X"][:, cols]
    y = table["y"]
    subj = table["subject"]
    out = {
        "table": table_name,
        "channel_set": channel_set,
        "channels": keep,
        "n_features": int(X.shape[1]),
        "n_epochs": int(X.shape[0]),
        "models": {},
    }
    for name in models:
        log.info("LOSO %s / %s / %s", table_name, channel_set, name)
        pred = loso_predict(X, y, subj, name)
        dest = C.CACHE_DIR / f"pred_{table_name}_{channel_set}_{name}.npz"
        np.savez_compressed(
            dest,
            y_true=pred["y_true"],
            y_pred=pred["y_pred"],
            y_score=pred["y_score"],
            subject=pred["subject"],
        )
        out["models"][name] = {"path": str(dest)}
    write_json(C.RESULTS_DIR / f"train_{table_name}_{channel_set}.json", out)
    return out


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--table", default="features_event")
    p.add_argument("--channels", default="all16")
    args = p.parse_args()
    run(args.table, args.channels)


if __name__ == "__main__":
    main()
