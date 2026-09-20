"""Evoked-response branch, fitted separately for each real EEG session."""
from dataclasses import dataclass
import hashlib

import numpy as np
from scipy.signal import butter, sosfiltfilt
from pyriemann.estimation import XdawnCovariances
from pyriemann.tangentspace import TangentSpace
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .shin import EEG_CHANNELS, FRONTAL
from .signal import Config, prepare


class ERPMeanBins(TransformerMixin, BaseEstimator):
    """Fixed five 200 ms bins in the post-stimulus second; no test-time fitting."""
    def __init__(self, sample_rate=200):
        self.sample_rate = sample_rate

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        pre = round(0.1 * self.sample_rate)
        width = round(0.2 * self.sample_rate)
        return np.concatenate([X[:, :, pre + i * width:pre + (i + 1) * width].mean(axis=-1)
                               for i in range(5)], axis=1)


def erp_config():
    return Config(sample_rate=200.0, channels=EEG_CHANNELS, frontal_channels=FRONTAL,
                  bands=((1.0, 30.0),), window_s=1.1, separation_s=1.5, step_s=0.1,
                  quality_highpass_hz=1.0, quality_lowpass_hz=30.0)


def extract_epochs(prepared, onset_times):
    fs = prepared.recording.sample_rate
    pre, post = round(0.1 * fs), round(1.0 * fs)
    accepted, epochs = [], []
    for index, time in enumerate(onset_times):
        center = round(float(time) * fs)
        start, end = center - pre, center + post
        if start < 0 or end > len(prepared.bad) or prepared.bad[start:end].any():
            continue
        epoch = prepared.filtered[0, :, start:end].copy()
        epoch -= epoch[:, :pre].mean(axis=-1, keepdims=True)
        epochs.append(epoch)
        accepted.append(index)
    shape = (0, len(prepared.recording.channels), pre + post)
    return np.stack(epochs) if epochs else np.empty(shape), np.asarray(accepted, dtype=int)


def classification_metrics(labels, scores):
    labels, scores = np.asarray(labels), np.asarray(scores)
    if len(labels) == 0:
        return {"trials": 0, "targets": 0, "target_prevalence": None, "auroc": None,
                "average_precision": None, "balanced_accuracy_margin_zero": None}
    two_classes = len(np.unique(labels)) == 2
    return {"trials": len(labels), "targets": int(labels.sum()), "target_prevalence": float(labels.mean()),
            "auroc": float(roc_auc_score(labels, scores)) if two_classes else None,
            "average_precision": float(average_precision_score(labels, scores)) if two_classes else None,
            "balanced_accuracy_margin_zero": float(balanced_accuracy_score(labels, scores >= 0)) if two_classes else None}


def eog_epochs(block, times):
    filtered = sosfiltfilt(butter(4, [1, 30], btype="bandpass", fs=200, output="sos"), block.eog, axis=1)
    epochs = []
    for time in times:
        center = round(time * 200)
        epoch = filtered[:, center - 20:center + 200].copy()
        if epoch.shape[1] != 220:
            raise ValueError("EOG epoch outside block.")
        epoch -= epoch[:, :20].mean(axis=1, keepdims=True)
        epochs.append(epoch)
    return np.stack(epochs) if epochs else np.empty((0, 2, 220))


@dataclass
class ERPModel:
    session_id: str
    kind: str
    classifier: Pipeline
    model_card: dict

    @property
    def config(self):
        return erp_config()

    def validate_recording(self, recording):
        if recording.session_id != self.session_id or recording.source != "replayed_eeg":
            raise ValueError("Real ERP model requires the same calibrated dataset session and provenance.")
        if tuple(recording.channels) != EEG_CHANNELS or recording.sample_rate != 200:
            raise ValueError("ERP channel/sample-rate contract mismatch.")
        if recording.processing_id != self.model_card["processing_id"]:
            raise ValueError("ERP input lacks the same calibrated ocular preprocessing.")

    def score(self, recording, epochs):
        self.validate_recording(recording)
        return self.classifier.decision_function(epochs) if len(epochs) else np.empty(0)

    def scan(self, recording):
        """Continuous candidate generation: recording samples only, no event markers."""
        if self.kind == "eog_bins":
            raise ValueError("The EOG control does not scan EEG or export burst events.")
        self.validate_recording(recording)
        prepared = prepare(recording, self.config)
        times = np.arange(0.1, recording.duration_s - 1.0, 0.1)
        epochs, valid = extract_epochs(prepared, times)
        return times[valid], self.score(recording, epochs), len(times) - len(valid)


def background_centres(trials, duration_s, step_s=0.5, exclusion_s=0.5):
    """Marker-free candidate onsets farther than exclusion_s from every stimulus onset."""
    onsets = np.asarray([t["time_s"] for t in trials], dtype=float)
    times = np.arange(0.1, duration_s - 1.0, step_s)
    if not len(onsets):
        return times
    distance = np.abs(times[:, None] - onsets[None, :]).min(axis=1)
    return times[distance > exclusion_s]


BACKGROUND = {"step_s": 0.5, "exclusion_s": 0.5}


def fit_erp(blocks, kind="xdawn"):
    if kind not in {"xdawn", "mean_bins", "eog_bins", "mean_bins_background"}:
        raise ValueError("Unknown ERP model kind.")
    if any(block.role != "calibration" for block in blocks):
        raise ValueError("Evaluation blocks cannot be passed into training.")
    if len({block.recording.session_id for block in blocks}) != 1:
        raise ValueError("Do not pool EEG sessions.")
    identities = {block.recording.processing_id for block in blocks}
    if len(identities) != 1 or next(iter(identities)) == "raw":
        raise ValueError("Use one frozen ocular preprocessing calibration before ERP training.")
    config = erp_config()
    Xs, ys, groups, quality = [], [], [], []
    for block in blocks:
        if block.condition not in (2, 3):
            continue
        prepared = prepare(block.recording, config)
        epochs, valid = extract_epochs(prepared, [t["time_s"] for t in block.trials])
        if kind == "eog_bins":
            epochs = eog_epochs(block, [block.trials[i]["time_s"] for i in valid])
        labels = np.asarray([t["label"] for t in block.trials])
        quality.append({"recording_id": block.recording.recording_id, "total_trials": len(labels),
                        "accepted_trials": len(valid), "accepted_targets": int(labels[valid].sum()),
                        "rejected_targets": int(labels.sum() - labels[valid].sum()),
                        "rejected_non_targets": int(len(labels) - labels.sum() - len(valid) + labels[valid].sum()),
                        "bad_or_edge_fraction": float(prepared.bad.mean())})
        block_labels = labels[valid]
        if kind == "mean_bins_background":
            # Calibration-only negatives from unlabeled times of the same blocks; the scan
            # grid is dominated by such windows, which stimulus-aligned training never sees.
            candidates = background_centres(block.trials, block.recording.duration_s, **BACKGROUND)
            background, accepted = extract_epochs(prepared, candidates)
            quality[-1].update({"background_candidates": int(len(candidates)),
                                "background_epochs": int(len(accepted))})
            if len(accepted):
                epochs = np.concatenate([epochs, background]) if len(valid) else background
                block_labels = np.r_[block_labels, np.zeros(len(accepted), dtype=int)]
        if len(block_labels):
            Xs.append(epochs)
            ys.extend(block_labels)
            groups.extend([block.block_index] * len(block_labels))
    if not Xs or len(ys) < 12 or len(np.unique(ys)) != 2:
        raise ValueError(f"Insufficient clean calibration trials: {quality}")
    X, y, groups = np.concatenate(Xs), np.asarray(ys), np.asarray(groups)
    splits = list(StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=19).split(X, y, groups))
    if any(len(np.unique(y[train])) < 2 or len(np.unique(y[test])) < 2 for train, test in splits):
        raise ValueError("A calibration CV fold lacks a class; report insufficient data, do not weaken split.")
    if kind == "xdawn":
        steps = [("covariance", XdawnCovariances(nfilter=3, classes=[1], applyfilters=True,
                                                 estimator="lwf", xdawn_estimator="lwf")),
                 ("tangent", TangentSpace(metric="riemann", tsupdate=False))]
    else:
        steps = [("mean_bins", ERPMeanBins())]
    steps += [("scale", StandardScaler()),
              ("linear", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=19))]
    search = GridSearchCV(Pipeline(steps), {"linear__C": [0.01, 0.1, 1.0, 10.0]},
                          cv=splits, scoring="average_precision", error_score="raise", n_jobs=1)
    search.fit(X, y)
    card = {"kind": kind, "source": "replayed_eeg", "session_id": blocks[0].recording.session_id,
            "processing_id": blocks[0].recording.processing_id,
            "signal_type": "evoked_response", "selected_C": float(search.best_params_["linear__C"]),
            "cv_average_precision": float(search.best_score_), "cv_is_model_selection_only": True,
            "training_trials": len(y), "training_targets": int(y.sum()), "quality": quality,
            "background_negatives": ({**BACKGROUND, "count": int(sum(q.get("background_epochs", 0) for q in quality)),
                                      "definition": "calibration-only grid centres farther than exclusion_s from every stimulus onset, labeled negative"}
                                     if kind == "mean_bins_background" else None),
            "training_recordings": [b.recording.recording_id for b in blocks],
            "training_hashes": [hashlib.sha256(b.recording.samples.tobytes()).hexdigest() for b in blocks],
            "folds": [{"train_blocks": np.unique(groups[tr]).tolist(), "validation_blocks": np.unique(groups[te]).tolist()}
                      for tr, te in splits], "C_grid": [0.01, 0.1, 1, 10],
            "channels": ["HEOG", "VEOG"] if kind == "eog_bins" else list(EEG_CHANNELS),
            "sample_rate": 200, "epoch_s": [-0.1, 1.0],
            "filter_hz": [1, 30], "baseline_s": [-0.1, 0], "artifact_amplitude_uv": 120,
            "artifact_step_uv": 60, "filter_guard_s": 2,
            "quality_highpass_hz": 1.0, "quality_lowpass_hz": 30.0,
            "input_preprocessing": "Separate pre-task EOG projection required; coefficients saved in session acquisition audit.",
            "interpretation": "Target-vs-nontarget EEG task proxy; sensory/motor/ocular contributions not isolated."}
    return ERPModel(blocks[0].recording.session_id, kind, search.best_estimator_, card)
