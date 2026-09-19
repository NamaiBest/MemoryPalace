"""Simulated continuous detection with persistence + cooldown.

Thresholds, k, and cooldown are chosen on training subjects only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.extract_features import extract_from_array, feature_names, load_table  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402
from src.preprocess import list_recordings, load_epochs, load_raw  # noqa: E402


def window_cache_path(subject: str, task: str) -> Path:
    return C.CACHE_DIR / f"{subject}_{task}_windows.npz"


def extract_windows_for_raw(raw, ch_names: list[str]) -> dict | None:
    sfreq = float(raw.info["sfreq"])
    win = int(round(C.STREAM_WINDOW_S * sfreq))
    hop = int(round(C.STREAM_HOP_S * sfreq))
    data = raw.get_data(picks=ch_names) * 1e6  # volts -> µV, matching epoch cache
    n_ch, n_times = data.shape
    if n_times < win:
        return None
    starts = np.arange(0, n_times - win + 1, hop, dtype=int)
    n = len(starts)
    cube = np.empty((n, n_ch, win), dtype=np.float32)
    for i, s in enumerate(starts):
        cube[i] = data[:, s : s + win]
    times = np.arange(win, dtype=np.float32) / sfreq
    X = extract_from_array(cube, times, sfreq, ch_names, window=(0.0, C.STREAM_WINDOW_S))
    onsets = starts / sfreq
    return {"X": X, "onsets": onsets.astype(np.float64), "sfreq": sfreq, "duration_s": n_times / sfreq}


def build_window_cache(force: bool = False) -> None:
    log = setup_logging("trigger")
    ensure_dirs()
    for rec in list_recordings():
        dest = window_cache_path(rec["subject"], rec["task"])
        if dest.exists() and not force:
            continue
        if load_epochs(rec["subject"], rec["task"]) is None:
            continue
        raw = load_raw(rec)
        if raw is None:
            continue
        pack = extract_windows_for_raw(raw, C.CHANNEL_NAMES)
        del raw
        if pack is None:
            continue
        ep = load_epochs(rec["subject"], rec["task"])
        surprise_onsets = ep["onsets"][ep["onset_types"] == C.TRIAL_TYPE_SURPRISE]
        np.savez_compressed(
            dest,
            X=pack["X"],
            onsets=pack["onsets"],
            surprise_onsets=surprise_onsets.astype(np.float64),
            duration_s=pack["duration_s"],
            subject=np.array(rec["subject"]),
            task=np.array(rec["task"]),
        )
        log.info("windows %s %s n=%s", rec["subject"], rec["task"], pack["X"].shape[0])


def load_windows(subject: str, task: str) -> dict | None:
    p = window_cache_path(subject, task)
    if not p.exists():
        return None
    z = np.load(p, allow_pickle=False)
    return {
        "X": z["X"],
        "onsets": z["onsets"],
        "surprise_onsets": z["surprise_onsets"],
        "duration_s": float(z["duration_s"]),
        "subject": str(z["subject"]),
        "task": str(z["task"]),
    }


def apply_trigger(onsets: np.ndarray, scores: np.ndarray, thr: float, k: int, cooldown_s: float) -> np.ndarray:
    """Return fire times (window onsets) after persistence + cooldown."""
    above = scores >= thr
    fires = []
    last_fire = -1e9
    run = 0
    for i, is_pos in enumerate(above):
        t = float(onsets[i])
        if t - last_fire < cooldown_s:
            run = 0
            continue
        run = run + 1 if is_pos else 0
        if run >= k:
            fires.append(t)
            last_fire = t
            run = 0
    return np.array(fires, dtype=np.float64)


def score_fires(fires: np.ndarray, surprise_onsets: np.ndarray, duration_s: float) -> dict:
    hits = []
    latencies = []
    matched = np.zeros(len(surprise_onsets), dtype=bool)
    false = 0
    for f in fires:
        d = f - surprise_onsets
        ok = (d >= 0) & (d <= C.DETECTION_WINDOW_S)
        if ok.any():
            j = int(np.argmin(np.where(ok, d, np.inf)))
            if not matched[j]:
                matched[j] = True
                hits.append(float(surprise_onsets[j]))
                latencies.append(float(d[j]))
            # extra fires in the same event window are absorbed (duplicate prevention)
        else:
            false += 1
    hours = duration_s / 3600.0 if duration_s > 0 else np.nan
    n_ev = len(surprise_onsets)
    return {
        "n_events": int(n_ev),
        "n_detected": int(matched.sum()),
        "n_missed": int(n_ev - matched.sum()),
        "detection_rate": float(matched.mean()) if n_ev else None,
        "n_fires": int(len(fires)),
        "n_false": int(false),
        "false_per_hour": float(false / hours) if hours else None,
        "bookmarks_per_hour": float(len(fires) / hours) if hours else None,
        "mean_latency_s": float(np.mean(latencies)) if latencies else None,
        "latencies": latencies,
        "duration_s": float(duration_s),
    }


def _fit_logreg(X: np.ndarray, y: np.ndarray) -> Pipeline:
    n0 = max(int((y == 0).sum()), 1)
    n1 = max(int((y == 1).sum()), 1)
    w = np.ones(len(y))
    w[y == 0] = 0.5 * len(y) / n0
    w[y == 1] = 0.5 * len(y) / n1
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000, class_weight="balanced", C=1.0, random_state=C.RANDOM_SEED
                ),
            ),
        ]
    )
    pipe.fit(X, y)
    return pipe


def _collect_subject_streams(subjects: np.ndarray) -> list[dict]:
    packs = []
    for subj in sorted(np.unique(subjects)):
        for task in C.TASKS:
            w = load_windows(str(subj), task)
            if w is not None:
                packs.append(w)
    return packs


def _eval_params(packs: list[dict], model, thr, k, cooldown) -> dict:
    parts = []
    for w in packs:
        scores = model.predict_proba(w["X"])[:, 1]
        fires = apply_trigger(w["onsets"], scores, thr, k, cooldown)
        parts.append(score_fires(fires, w["surprise_onsets"], w["duration_s"]))
    det = [p["detection_rate"] for p in parts if p["detection_rate"] is not None]
    fp = [p["false_per_hour"] for p in parts if p["false_per_hour"] is not None]
    lat = [p["mean_latency_s"] for p in parts if p["mean_latency_s"] is not None]
    hours = sum(p["duration_s"] for p in parts) / 3600.0
    n_false = sum(p["n_false"] for p in parts)
    n_det = sum(p["n_detected"] for p in parts)
    n_ev = sum(p["n_events"] for p in parts)
    return {
        "detection_rate": float(np.mean(det)) if det else None,
        "false_per_hour": float(n_false / hours) if hours else None,
        "bookmarks_per_hour": float(sum(p["n_fires"] for p in parts) / hours) if hours else None,
        "mean_latency_s": float(np.mean(lat)) if lat else None,
        "n_events": int(n_ev),
        "n_detected": int(n_det),
        "n_recordings": len(parts),
        "pooled_detection_rate": float(n_det / n_ev) if n_ev else None,
    }


def choose_operating_point(train_packs, model, train_epoch_scores) -> dict:
    """Pick (thr, k, cooldown) on training data only.

    Preference: false/hour <= TARGET, then highest detection rate.
    If none meet the FP cap, take the lowest FP among k>=2.
    """
    candidates = []
    for q in C.THRESHOLD_QUANTILES:
        thr = float(np.quantile(train_epoch_scores, q))
        for k in C.PERSIST_K_CANDIDATES:
            for cd in C.COOLDOWN_S_CANDIDATES:
                ev = _eval_params(train_packs, model, thr, k, cd)
                ev.update({"thr": thr, "k": k, "cooldown_s": cd, "score_quantile": q})
                candidates.append(ev)
    cap = C.TRIGGER_TARGET_MAX_FP_PER_HOUR
    ok = [c for c in candidates if c["false_per_hour"] is not None and c["false_per_hour"] <= cap]
    if ok:
        ok.sort(key=lambda c: (-(c["pooled_detection_rate"] or 0), c["false_per_hour"]))
        chosen = ok[0]
    else:
        rest = [c for c in candidates if c["k"] >= 2]
        rest.sort(key=lambda c: (c["false_per_hour"] if c["false_per_hour"] is not None else 1e9))
        chosen = rest[0] if rest else candidates[0]
    chosen["n_candidates"] = len(candidates)
    return chosen


def run(force_windows: bool = False) -> dict:
    log = setup_logging("trigger")
    ensure_dirs()
    build_window_cache(force=force_windows)
    table = load_table("features_event")
    X, y, subj = table["X"], table["y"].astype(int), table["subject"]
    uniq = np.array(sorted(np.unique(subj)))
    fold_rows = []
    chosen_ops = []
    for held in uniq:
        tr = subj != held
        if y[tr].sum() == 0 or (y[tr] == 0).sum() == 0:
            continue
        model = _fit_logreg(X[tr], y[tr])
        train_subj = np.unique(subj[tr])
        train_packs = _collect_subject_streams(train_subj)
        if not train_packs:
            continue
        train_scores = model.predict_proba(X[tr])[:, 1]
        op = choose_operating_point(train_packs, model, train_scores)
        test_packs = _collect_subject_streams(np.array([held]))
        test_ev = _eval_params(test_packs, model, op["thr"], op["k"], op["cooldown_s"]) if test_packs else None
        fold_rows.append(
            {
                "subject": str(held),
                "op": {"thr": op["thr"], "k": op["k"], "cooldown_s": op["cooldown_s"], "score_quantile": op["score_quantile"]},
                "train_op_metrics": {
                    "detection_rate": op["pooled_detection_rate"],
                    "false_per_hour": op["false_per_hour"],
                },
                "test": test_ev,
            }
        )
        chosen_ops.append(op)
        log.info(
            "trigger LOSO %s k=%s cd=%s q=%s test det=%s fp/h=%s lat=%s",
            held,
            op["k"],
            op["cooldown_s"],
            op["score_quantile"],
            None if not test_ev else test_ev["pooled_detection_rate"],
            None if not test_ev else test_ev["false_per_hour"],
            None if not test_ev else test_ev["mean_latency_s"],
        )

    tests = [r["test"] for r in fold_rows if r["test"]]
    def _mean(key):
        vals = [t[key] for t in tests if t.get(key) is not None]
        return {"mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1) if len(vals) > 1 else 0.0)} if vals else None

    summary = {
        "model": "logreg",
        "channel_set": "all16",
        "detection_window_s": C.DETECTION_WINDOW_S,
        "stream_window_s": C.STREAM_WINDOW_S,
        "stream_hop_s": C.STREAM_HOP_S,
        "n_subjects": len(fold_rows),
        "loso": {
            "detection_rate": _mean("pooled_detection_rate"),
            "false_triggers_per_hour": _mean("false_per_hour"),
            "bookmarks_per_hour": _mean("bookmarks_per_hour"),
            "mean_latency_s": _mean("mean_latency_s"),
        },
        "folds": fold_rows,
        "note": (
            "Operating point (threshold quantile, consecutive windows k, cooldown) "
            "is chosen on training subjects' continuous streams only."
        ),
    }
    write_json(C.RESULTS_DIR / "continuous_trigger.json", summary)
    return summary


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--force-windows", action="store_true")
    args = p.parse_args()
    run(force_windows=args.force_windows)


if __name__ == "__main__":
    main()
