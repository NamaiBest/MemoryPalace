"""Does a small channel set carry the aligned target signal? Development-data check.

All participants here are already inspected. Known-onset (marker-aligned) AUROC only;
no continuous scan, no threshold, nothing frozen. Feature sets are fixed in advance:
two fitted-nothing physiological features and three channel subsets of the existing
mean-amplitude-bin classifier under the existing calibration folds.
"""
from dataclasses import replace
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import write_json
from .erp import ERPMeanBins, classification_metrics, erp_config, extract_epochs
from .shin import EEG_CHANNELS, correct_ocular_from_pretask, load_session
from .signal import prepare
from .workload_benchmark import file_hash, utc_now

PARTICIPANTS = ("VP001", "VP002", "VP005", "VP006")
CHANNEL_SETS = {"full": EEG_CHANNELS, "midline": ("AFz", "Cz", "Pz", "POz"), "c3c4": ("C3", "C4")}
DESCRIPTOR_CLUSTER = ("F1", "F2", "FC1", "FC2", "Cz", "CP1", "CP2", "Pz")
FIXED = {"fixed_pz_p300": ("Pz mean amplitude 0.3-0.6 s after onset, baseline-corrected; positive = target-like", None),
         "fixed_c4_minus_c3": ("C4 minus C3 mean amplitude 0.2-0.8 s after onset; tests response-hand lateralization", None),
         # Added after the first run, from the data descriptor (Shin et al. 2018): the largest
         # target/non-target difference is at 0.2-0.4 s over frontal, central and parietal sites.
         "fixed_pz_200_400": ("Pz mean amplitude 0.2-0.4 s after onset (descriptor window)", None),
         "fixed_cz_200_400": ("Cz mean amplitude 0.2-0.4 s after onset (descriptor window)", None),
         "fixed_cluster_200_400": ("mean over F1 F2 FC1 FC2 Cz CP1 CP2 Pz, 0.2-0.4 s after onset (descriptor window)", None)}
RULE = {"threshold": 0.70, "minimum_sessions": 7, "of_sessions": 12,
        "statement": "midline bins or a fixed feature reach evaluation AUROC >= 0.70 in at least 7 of 12 sessions"}


def indices(channels):
    return [EEG_CHANNELS.index(c) for c in channels]


def fixed_scores(epochs, name, sample_rate=200):
    pre = round(0.1 * sample_rate)
    if name == "fixed_pz_p300":
        window = slice(pre + round(0.3 * sample_rate), pre + round(0.6 * sample_rate))
        return epochs[:, EEG_CHANNELS.index("Pz"), window].mean(axis=-1)
    if name == "fixed_c4_minus_c3":
        window = slice(pre + round(0.2 * sample_rate), pre + round(0.8 * sample_rate))
        return (epochs[:, EEG_CHANNELS.index("C4"), window] - epochs[:, EEG_CHANNELS.index("C3"), window]).mean(axis=-1)
    window = slice(pre + round(0.2 * sample_rate), pre + round(0.4 * sample_rate))
    if name == "fixed_pz_200_400":
        return epochs[:, EEG_CHANNELS.index("Pz"), window].mean(axis=-1)
    if name == "fixed_cz_200_400":
        return epochs[:, EEG_CHANNELS.index("Cz"), window].mean(axis=-1)
    if name == "fixed_cluster_200_400":
        return epochs[:, indices(DESCRIPTOR_CLUSTER), window].mean(axis=(-2, -1))
    raise ValueError("Unknown fixed feature.")


def fit_subset(X, y, groups, channels):
    """Same pipeline, grid, folds and scoring as fit_erp(kind='mean_bins'), on a channel subset."""
    X = X[:, indices(channels), :]
    splits = list(StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=19).split(X, y, groups))
    if any(len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2 for tr, te in splits):
        raise ValueError("A calibration fold lacks a class.")
    pipeline = Pipeline([("mean_bins", ERPMeanBins()), ("scale", StandardScaler()),
                         ("linear", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=19))])
    search = GridSearchCV(pipeline, {"linear__C": [0.01, 0.1, 1.0, 10.0]}, cv=splits,
                          scoring="average_precision", error_score="raise", n_jobs=1)
    search.fit(X, y)
    return search


def aligned_epochs(blocks, highpass_hz=1.0):
    """Marker-aligned epochs; the analysis band can be widened below the default 1 Hz."""
    config = replace(erp_config(), bands=((highpass_hz, 30.0),))
    Xs, ys, groups = [], [], []
    for block in blocks:
        if block.condition not in (2, 3):
            continue
        epochs, valid = extract_epochs(prepare(block.recording, config), [t["time_s"] for t in block.trials])
        labels = np.asarray([t["label"] for t in block.trials])[valid]
        if len(valid):
            Xs.append(epochs)
            ys.extend(labels.tolist())
            groups.extend([block.block_index] * len(valid))
    return np.concatenate(Xs), np.asarray(ys), np.asarray(groups)


def check_session(directory, session, highpass_hz=1.0):
    blocks, _ = load_session(directory, session)
    blocks, _ = correct_ocular_from_pretask(directory, session, blocks, _)
    X_cal, y_cal, g_cal = aligned_epochs([b for b in blocks if b.role == "calibration"], highpass_hz)
    X_ev, y_ev, _ = aligned_epochs([b for b in blocks if b.role == "evaluation"], highpass_hz)
    row = {"session": session, "session_id": blocks[0].recording.session_id,
           "calibration_trials": int(len(y_cal)), "calibration_targets": int(y_cal.sum()),
           "evaluation_trials": int(len(y_ev)), "evaluation_targets": int(y_ev.sum()), "features": {}}
    for name in FIXED:
        row["features"][name] = {"fitted": False,
                                 "calibration": classification_metrics(y_cal, fixed_scores(X_cal, name)),
                                 "evaluation": classification_metrics(y_ev, fixed_scores(X_ev, name))}
    for name, channels in CHANNEL_SETS.items():
        search = fit_subset(X_cal, y_cal, g_cal, channels)
        scores = search.best_estimator_.decision_function(X_ev[:, indices(channels), :])
        row["features"][name] = {"fitted": True, "channels": list(channels), "n_features": 5 * len(channels),
                                 "selected_C": float(search.best_params_["linear__C"]),
                                 "calibration_cv_average_precision": float(search.best_score_),
                                 "evaluation": classification_metrics(y_ev, scores)}
    return row


def run_channel_check(data_root, out, participants=PARTICIPANTS, highpass_hz=1.0):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory is not empty; preserve previous results.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    started = utc_now()
    results = {}
    for participant in participants:
        directory = Path(data_root) / participant
        results[participant] = []
        for session in (1, 2, 3):
            print(f"{participant} session {session}: aligned epochs ({highpass_hz:g}-30 Hz), fixed features and channel subsets", flush=True)
            results[participant].append(check_session(directory, session, highpass_hz))
    names = list(FIXED) + list(CHANNEL_SETS)
    summary = {}
    for name in names:
        values = [r["features"][name]["evaluation"]["auroc"] for rows in results.values() for r in rows]
        summary[name] = {"evaluation_auroc_by_session": values, "mean": float(np.mean(values)),
                         "sessions_at_or_above_threshold": int(sum(v >= RULE["threshold"] for v in values)),
                         "per_participant_mean": {p: float(np.mean([r["features"][name]["evaluation"]["auroc"] for r in rows]))
                                                  for p, rows in results.items()}}
    rule_met = any(summary[name]["sessions_at_or_above_threshold"] >= RULE["minimum_sessions"]
                   for name in ("midline", *FIXED))
    report = {"purpose": "development-data check of aligned target discrimination by channel set; nothing frozen, no continuous scan",
              "started_utc": started, "completed_utc": utc_now(), "participants_all_previously_inspected": True,
              "erp_band_hz": [highpass_hz, 30.0], "quality_band_hz": [1.0, 30.0],
              "fixed_features": {k: v[0] for k, v in FIXED.items()}, "channel_sets": {k: list(v) for k, v in CHANNEL_SETS.items()},
              "rule": RULE, "rule_met": rule_met, "summary": summary, "sessions": results,
              "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sorted((root / "eeg_moments").glob("*.py"))}}
    write_json(out / "report.json", report)
    write_results(report, out)
    return report


def fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def write_results(report, out):
    names = list(report["fixed_features"]) + list(report["channel_sets"])
    lines = [f"# Aligned target discrimination by channel set (development data; ERP band {report['erp_band_hz'][0]:g}-30 Hz)", "",
             "Known-onset AUROC on the held-out 2-/3-back blocks of each session, all participants previously inspected. "
             "Fixed features fit nothing. Channel-subset classifiers use the existing mean-amplitude-bin pipeline, C grid, "
             "block-grouped folds and scoring on the calibration blocks only. No continuous scan and no threshold selection.", "",
             "| Participant | Session | " + " | ".join(names) + " | Evaluation trials (targets) |",
             "|---|---|" + "---:|" * len(names) + "---:|"]
    for participant, rows in report["sessions"].items():
        for r in rows:
            cells = " | ".join(fmt(r["features"][n]["evaluation"]["auroc"]) for n in names)
            lines.append(f"| {participant} | {r['session']} | {cells} | {r['evaluation_trials']} ({r['evaluation_targets']}) |")
    lines += ["", "| Feature set | Mean AUROC over 12 sessions | Sessions at or above 0.70 | " + " | ".join(report["sessions"]) + " |",
              "|---|---:|---:|" + "---:|" * len(report["sessions"])]
    for n in names:
        s = report["summary"][n]
        lines.append(f"| {n} | {s['mean']:.3f} | {s['sessions_at_or_above_threshold']}/12 | "
                     + " | ".join(f"{s['per_participant_mean'][p]:.2f}" for p in report["sessions"]) + " |")
    lines += ["", "Fixed features (calibration blocks, 24 targets per session; no fitting so these are additional evidence, not training):", "",
              "| Participant | Session | " + " | ".join(f"{n} calibration AUROC" for n in report["fixed_features"]) + " |",
              "|---|---|" + "---:|" * len(report["fixed_features"])]
    for participant, rows in report["sessions"].items():
        for r in rows:
            lines.append(f"| {participant} | {r['session']} | " + " | ".join(fmt(r["features"][n]["calibration"]["auroc"]) for n in report["fixed_features"]) + " |")
    lines += ["", f"Prespecified rule: {report['rule']['statement']}. **Met: {report['rule_met']}.**", "",
              "AUROC on 11–12 targets per session has a standard deviation near 0.1; read the mean and the count of sessions, not single cells. "
              "Fixed-feature AUROC below 0.5 means the deflection has the opposite sign from the stated convention. "
              "This checks whether an aligned signal exists in a small channel set; it says nothing about marker-free scanning, "
              "which failed for VP001 despite an aligned AUROC near 0.78.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))
