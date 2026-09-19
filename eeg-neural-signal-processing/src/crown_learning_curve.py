"""How many calibration trials does a Crown wearer need? Measured, not guessed.

Two questions this answers, both of which gate hardware day:

  1. CALIBRATION BUDGET. Weights do not transfer between people or sessions, so every
     wearer must be retrained on the day. How many trials buys usable accuracy? That
     number decides the session schedule, and nothing else in this repo measures it.

  2. IS THE PIPELINE THE RIGHT ONE? `crown_exact.py` uses CSP + LDA. The design handoff
     argues for covariances -> tangent space -> regularised logistic regression, on the
     grounds that Riemannian methods beat alternatives at a few hundred trials from one
     subject. That is a testable claim, so it is tested here rather than assumed.

Data: EEGMMIDB, imagined left vs right fist, restricted to the Neurosity Crown's exact
8 channel positions (F5 F6 C3 C4 CP3 CP4 PO3 PO4). No channel substitution.

This is motor imagery, NOT confusion. No public dataset labels confusion on this
montage — that was checked from several directions and it does not exist. What transfers
is the *shape* of the curve: how quickly a within-subject model on these 8 electrodes
becomes useful. Treat the absolute numbers as belonging to motor imagery only.

    ../eeg-neural-signal-processing/.venv/bin/python src/crown_learning_curve.py
"""
import json
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
import mne

mne.set_log_level("ERROR")

from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from mne.decoding import CSP

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data", "eegmmidb")
RESULTS = os.path.join(os.path.dirname(HERE), "results", "crown_learning_curve.json")

CROWN = ["F5", "F6", "C3", "C4", "Cp3", "Cp4", "Po3", "Po4"]
# Runs 4, 8 and 12 are the imagined-movement runs; 3, 7 and 11 are executed movement
# and are deliberately excluded. That caps a subject at roughly 45 trials, so the
# curve stops at 28 — about what is left after holding out 30% for testing.
RUNS = [4, 8, 12]
TRAIN_SIZES = [8, 12, 16, 20, 24, 28]
MIN_TRIALS = 40
REPEATS = 5
SEED = 17


def norm(channel):
    return channel.replace(".", "").strip().capitalize()


def pipelines():
    """CSP+LDA is what the repo ships; tangent space is what the handoff argues for."""
    return {
        "csp_lda": Pipeline([
            ("csp", CSP(n_components=4, log=True)),
            ("lda", LDA(solver="eigen", shrinkage="auto")),
        ]),
        "tangent_logreg": make_pipeline(
            Covariances(estimator="oas"),
            TangentSpace(metric="riemann"),
            StandardScaler(),
            LogisticRegression(C=0.1, max_iter=2000),
        ),
    }


def load_subject(subject):
    """All trials for one subject, Crown's 8 channels only. None if any are missing."""
    epochs, labels = [], []
    for run in RUNS:
        path = os.path.join(DATA, f"S{subject:03d}R{run:02d}.edf")
        if not os.path.exists(path):
            return None, None
        raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
        raw.rename_channels({c: norm(c) for c in raw.ch_names})
        if any(c not in raw.ch_names for c in CROWN):
            return None, None
        raw.pick(CROWN)
        raw.filter(7.0, 30.0, verbose=False)
        events, event_id = mne.events_from_annotations(raw, verbose=False)
        wanted = {k: v for k, v in event_id.items() if k in ("T1", "T2")}
        if len(wanted) < 2:
            continue
        epoched = mne.Epochs(raw, events, wanted, tmin=0.5, tmax=3.5,
                             baseline=None, preload=True, verbose=False)
        if len(epoched) == 0:
            continue
        epochs.append(epoched.get_data())
        labels.append(np.array([1 if e == wanted["T2"] else 0
                                for e in epoched.events[:, 2]]))
    if not epochs:
        return None, None
    return np.concatenate(epochs), np.concatenate(labels)


def curve_for_subject(X, y, rng):
    """AUC at each training-set size, averaged over repeated random splits.

    Every split holds out the same 30% for testing, so the only thing varying across
    sizes is how much training data the model saw. Scored with AUC rather than accuracy
    because it does not depend on a threshold, which is the point the handoff makes
    about ranking rather than thresholding.
    """
    out = {}
    splitter = StratifiedShuffleSplit(n_splits=REPEATS, test_size=0.3,
                                      random_state=rng)
    splits = list(splitter.split(X, y))
    for size in TRAIN_SIZES:
        for name, _ in pipelines().items():
            out.setdefault(name, {})
        for name in out:
            scores = []
            for train_idx, test_idx in splits:
                if len(train_idx) < size:
                    continue
                # Subsample the training pool while keeping both classes present.
                pool = train_idx[:size]
                if len(np.unique(y[pool])) < 2:
                    continue
                try:
                    model = pipelines()[name]
                    model.fit(X[pool], y[pool])
                    if hasattr(model, "predict_proba"):
                        scores.append(roc_auc_score(y[test_idx],
                                                    model.predict_proba(X[test_idx])[:, 1]))
                    else:
                        scores.append(roc_auc_score(y[test_idx],
                                                    model.decision_function(X[test_idx])))
                except Exception:
                    continue
            if scores:
                out[name][size] = float(np.mean(scores))
    return out


def main():
    if not os.path.isdir(DATA):
        sys.exit(f"EEGMMIDB not found at {DATA}. Run: src/download.py eegmmidb")

    print("=" * 78)
    print("CALIBRATION LEARNING CURVE - Neurosity Crown's exact 8 channels")
    print("EEGMMIDB imagined left vs right fist. Motor imagery, not confusion.")
    print("=" * 78)

    per_subject = {name: {size: [] for size in TRAIN_SIZES} for name in pipelines()}
    used = 0
    for subject in range(1, 110):
        X, y = load_subject(subject)
        if X is None or len(np.unique(y)) < 2 or len(y) < MIN_TRIALS:
            continue
        curve = curve_for_subject(X, y, SEED + subject)
        for name, sizes in curve.items():
            for size, auc in sizes.items():
                per_subject[name][size].append(auc)
        used += 1
        if used % 20 == 0:
            print(f"  ...{used} subjects")

    print(f"\nSubjects with all 8 Crown channels and enough trials: {used}\n")
    header = "  trials  " + "".join(f"{n:>18s}" for n in per_subject)
    print(header)
    print("  " + "-" * (len(header) - 2))

    summary = {}
    for size in TRAIN_SIZES:
        row = f"  {size:>6d}  "
        for name in per_subject:
            values = per_subject[name][size]
            if values:
                mean = float(np.mean(values))
                summary.setdefault(name, {})[size] = {
                    "mean_auc": mean,
                    "sd": float(np.std(values)),
                    "n_subjects": len(values),
                    "frac_ge_70": float(np.mean(np.array(values) >= 0.70)),
                }
                row += f"{mean:>18.3f}"
            else:
                row += f"{'-':>18s}"
        print(row)

    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w") as handle:
        json.dump({
            "dataset": "EEGMMIDB imagined left vs right fist",
            "channels": CROWN,
            "task_is_confusion": False,
            "note": "Motor imagery. No public dataset labels confusion on this montage.",
            "metric": "roc_auc, within-subject, mean over repeated stratified splits",
            "repeats": REPEATS,
            "results": summary,
        }, handle, indent=2)
    print(f"\nsaved -> {RESULTS}")


if __name__ == "__main__":
    main()
