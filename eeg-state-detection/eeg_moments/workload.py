"""Session-calibrated sustained activity scorers; task labels are proxies."""
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib

import numpy as np
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from scipy.signal import butter, sosfiltfilt
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .shin import EEG_CHANNELS, FRONTAL
from .signal import Config, prepare

KINDS = ("power", "tangent", "eog_power")
TARGETS = ("task_rest", "high_low")
C_GRID = [0.01, 0.1, 1.0, 10.0]


def workload_config():
    return Config(sample_rate=200.0, channels=EEG_CHANNELS, frontal_channels=FRONTAL,
                  window_s=2.0, context_offset_s=3.0,
                  quality_highpass_hz=1.0, quality_lowpass_hz=30.0)


def extract_workload_windows(prepared, step_s=2.0):
    """The full uniform grid is retained, including invalid centers, for segmentation."""
    fs = prepared.recording.sample_rate
    width, step = round(2 * fs), round(step_s * fs)
    if step < 1:
        raise ValueError("Window step is shorter than one sample.")
    centers = np.arange(width // 2, len(prepared.bad) - width // 2 + 1, step)
    accepted, epochs = [], []
    for index, center in enumerate(centers):
        start, end = center - width // 2, center + width // 2
        if not prepared.bad[start:end].any():
            accepted.append(index)
            epochs.append(prepared.filtered[:, :, start:end])
    shape = (0, prepared.filtered.shape[0], len(prepared.recording.channels), width)
    return (np.stack(epochs) if epochs else np.empty(shape), centers / fs,
            np.asarray(accepted, dtype=int))


def labels_for_times(block, times, target):
    """Labels require the whole two-second feature window inside a labeled interval."""
    if target not in TARGETS:
        raise ValueError("Unknown workload target.")
    times = np.asarray(times)
    labels = np.full(len(times), -1, dtype=int)
    task = (times - 1 >= block.task_start_s + 2) & (times + 1 <= block.task_end_s - 2)
    if target == "task_rest":
        for start, end in block.baseline_intervals_s:
            labels[(times - 1 >= start) & (times + 1 <= end)] = 0
        labels[task] = 1
    else:
        labels[task] = int(block.condition in (2, 3))
    return labels


def workload_features(epochs, kind):
    if kind in ("power", "eog_power"):
        return np.log(np.maximum(epochs.var(axis=-1), 1e-12)).reshape(len(epochs), -1)
    if kind != "tangent":
        raise ValueError("Unknown workload feature kind.")
    n, bands, channels, width = epochs.shape
    flat = epochs.reshape(-1, channels, width)
    flat = flat - flat.mean(axis=-1, keepdims=True)
    return Covariances(estimator="lwf").transform(flat).reshape(n, bands, channels, channels)


class SustainedTangentFeatures(TransformerMixin, BaseEstimator):
    """No ERP prototype, context subtraction, or test-batch reference fitting."""
    def fit(self, X, y=None):
        self.maps_ = [TangentSpace(metric="riemann", tsupdate=False).fit(X[:, b])
                      for b in range(X.shape[1])]
        return self

    def transform(self, X):
        return np.concatenate([mapping.transform(X[:, b])
                               for b, mapping in enumerate(self.maps_)], axis=1)


def eye_windows(block, times):
    config = workload_config()
    filtered = np.stack([sosfiltfilt(butter(4, band, btype="bandpass", fs=200, output="sos"),
                                    block.eog, axis=1) for band in config.bands])
    epochs = [filtered[:, :, round(time * 200) - 200:round(time * 200) + 200] for time in times]
    return np.stack(epochs) if epochs else np.empty((0, 3, 2, 400))


def segment_scores(times, scores, minimum_s=3.0):
    """Invalid/negative centers break an interval; never bridge a missing grid point."""
    times, scores = np.asarray(times), np.asarray(scores)
    if times.shape != scores.shape or (len(times) > 1 and not np.allclose(np.diff(times), 0.25)):
        raise ValueError("Segmentation requires the full 0.25 second grid.")
    intervals, onset, confirmed, peak = [], None, None, None
    for time, score in zip(times, scores):
        if not np.isfinite(score) or score < 0:
            if confirmed is not None:
                intervals.append({"start_s": onset, "confirmed_s": confirmed,
                                  "end_s": float(time), "peak_score": peak})
            onset, confirmed, peak = None, None, None
            continue
        if onset is None:
            onset, peak = float(time), float(score)
        peak = max(peak, float(score))
        if confirmed is None and time - onset >= minimum_s:
            confirmed = float(time)
    if confirmed is not None:
        intervals.append({"start_s": onset, "confirmed_s": confirmed,
                          "end_s": float(times[-1]), "peak_score": peak})
    return intervals


@dataclass
class WorkloadModel:
    session_id: str
    kind: str
    target: str
    classifier: Pipeline
    model_card: dict

    def validate_recording(self, recording):
        recording.validate()
        if recording.session_id != self.session_id or recording.source != "replayed_eeg":
            raise ValueError("Workload model requires the same calibrated real-data session and provenance.")
        if tuple(recording.channels) != EEG_CHANNELS or recording.sample_rate != 200:
            raise ValueError("Workload channel/sample-rate contract mismatch.")
        if recording.processing_id != self.model_card["processing_id"]:
            raise ValueError("Workload input lacks the same calibrated ocular preprocessing.")

    def score_features(self, recording, features):
        self.validate_recording(recording)
        return self.classifier.decision_function(features) if len(features) else np.empty(0)

    def scan(self, recording):
        """Marker-free inference: no RealBlock, task intervals or trial timestamps."""
        self.validate_recording(recording)
        if self.kind == "eog_power":
            raise ValueError("The eye-only control cannot scan EEG or export EEG events.")
        epochs, times, accepted = extract_workload_windows(prepare(recording, workload_config()), 0.25)
        scores = np.full(len(times), np.nan)
        if len(accepted):
            scores[accepted] = self.score_features(recording, workload_features(epochs, self.kind))
        return {"times": times, "scores": scores, "valid": np.isfinite(scores),
                "stretches": segment_scores(times, scores)}


def fit_workload(blocks, kind="power", target="task_rest"):
    if kind not in KINDS or target not in TARGETS:
        raise ValueError("Unknown workload model/target.")
    if not blocks or any(b.role != "calibration" for b in blocks):
        raise ValueError("Only calibration blocks may enter workload training.")
    if len({b.recording.session_id for b in blocks}) != 1:
        raise ValueError("Do not pool EEG sessions.")
    identities = {b.recording.processing_id for b in blocks}
    if len(identities) != 1 or next(iter(identities)) == "raw":
        raise ValueError("Use one frozen ocular preprocessing calibration before workload training.")
    if Counter(b.condition for b in blocks) != Counter({0: 2, 2: 2, 3: 2}):
        raise ValueError("Require exactly two calibration blocks per n-back condition.")
    ordered = sorted(blocks, key=lambda b: b.block_index)
    if any(a.original_offset_s + a.recording.duration_s > b.original_offset_s + 0.005
           for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Calibration block contexts overlap.")
    hashes = [hashlib.sha256(b.recording.samples.tobytes()).hexdigest() for b in ordered]
    if len(set(hashes)) != len(hashes) or len({b.recording.recording_id for b in ordered}) != len(ordered):
        raise ValueError("Calibration blocks must be distinct.")
    Xs, ys, groups, repetitions, quality = [], [], [], [], []
    occurrences = Counter()
    for block in ordered:
        if block.recording.source != "replayed_eeg":
            raise ValueError("The real workload experiment requires replayed EEG.")
        epochs, times, accepted = extract_workload_windows(prepare(block.recording, workload_config()))
        labels = labels_for_times(block, times, target)
        use = labels[accepted] >= 0
        quality.append({"recording_id": block.recording.recording_id, "condition": block.condition,
                        "labeled_windows": int((labels >= 0).sum()), "accepted_windows": int(use.sum()),
                        "positive_windows": int((labels[accepted][use] == 1).sum())})
        occurrences[block.condition] += 1
        if not use.any():
            raise ValueError(f"Calibration block has no usable labeled windows: {quality[-1]}")
        if kind == "eog_power":
            epochs = eye_windows(block, times[accepted])
        Xs.append(workload_features(epochs[use], kind))
        ys.extend(labels[accepted][use])
        groups.extend([block.block_index] * int(use.sum()))
        repetitions.extend([occurrences[block.condition]] * int(use.sum()))
    X, y, groups, repetitions = np.concatenate(Xs), np.asarray(ys), np.asarray(groups), np.asarray(repetitions)
    splits = [(np.flatnonzero(repetitions != r), np.flatnonzero(repetitions == r)) for r in (1, 2)]
    if any(len(np.unique(y[tr])) != 2 or len(np.unique(y[va])) != 2 for tr, va in splits):
        raise ValueError("Calibration CV lacks a class; do not weaken the split.")
    steps = [("tangent", SustainedTangentFeatures())] if kind == "tangent" else []
    steps += [("scale", StandardScaler()),
              ("linear", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=19))]
    search = GridSearchCV(Pipeline(steps), {"linear__C": C_GRID}, cv=splits, scoring="roc_auc",
                          error_score="raise", n_jobs=1)
    search.fit(X, y)
    card = {"kind": kind, "target": target, "source": "replayed_eeg",
            "session_id": ordered[0].recording.session_id, "processing_id": next(iter(identities)),
            "config": asdict(workload_config()), "selected_C": float(search.best_params_["linear__C"]),
            "C_grid": C_GRID, "selection_cv_auroc": float(search.best_score_),
            "cv_auroc_by_C": search.cv_results_["mean_test_score"].tolist(),
            "cv_is_model_selection_only": True, "training_windows": len(y), "positives": int(y.sum()),
            "training_recordings": [b.recording.recording_id for b in ordered],
            "training_sample_sha256": hashes, "quality": quality,
            "folds": [{"train_blocks": np.unique(groups[tr]).tolist(),
                       "validation_blocks": np.unique(groups[va]).tolist()} for tr, va in splits],
            "score": "uncalibrated linear decision margin; >=0 for at least 3 seconds emits an interval",
            "interpretation": "Task/rest or higher/lower n-back proxy, not a measured mental state."}
    return WorkloadModel(ordered[0].recording.session_id, kind, target, search.best_estimator_, card)


def workload_metrics(labels, scores, threshold=0.0):
    labels, scores = np.asarray(labels), np.asarray(scores)
    if labels.shape != scores.shape or not np.isfinite(scores).all() or not np.isin(labels, [0, 1]).all():
        raise ValueError("Metrics require matching finite scores and binary labels.")
    positive, negative = labels == 1, labels == 0
    pred = scores >= threshold
    sensitivity = float(pred[positive].mean()) if positive.any() else None
    specificity = float((~pred[negative]).mean()) if negative.any() else None
    two = positive.any() and negative.any()
    return {"windows": len(labels), "positives": int(positive.sum()),
            "positive_prevalence": float(positive.mean()) if len(labels) else None,
            "auroc": float(roc_auc_score(labels, scores)) if two else None,
            "average_precision": float(average_precision_score(labels, scores)) if two else None,
            "balanced_accuracy": (sensitivity + specificity) / 2 if two else None,
            "sensitivity": sensitivity, "specificity": specificity, "threshold": threshold}


def export_workload_events(recording, model, scan, offset_s=0.0):
    model.validate_recording(recording)
    if model.kind.startswith("eog_") or not np.isfinite(offset_s) or offset_s < 0:
        raise ValueError("Only EEG models and a finite nonnegative clock offset can export EEG events.")
    ranked = sorted(scan["stretches"], key=lambda s: (-s["peak_score"], s["start_s"]))
    events = []
    for rank, stretch in enumerate(ranked, 1):
        key = f"{recording.recording_id}:{model.kind}:{model.target}:{stretch['start_s']:.6f}:{offset_s:.6f}"
        fraction = (rank - 1) / len(ranked)
        events.append({"event_id": "eeg-workload-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                       "session_id": recording.session_id, "eeg_session_id": recording.session_id,
                       "recording_id": recording.recording_id, "source": "replayed_eeg",
                       "signal_type": "stretch", "event_type": "eeg_workload_candidate",
                       "model_target": model.target, "start_s": stretch["start_s"] + offset_s,
                       "end_s": stretch["end_s"] + offset_s, "anchor_s": stretch["start_s"] + offset_s,
                       "eeg_anchor_s": stretch["start_s"], "offset_s": offset_s,
                       "confirmed_s": stretch["confirmed_s"] + offset_s,
                       "duration_s": stretch["end_s"] - stretch["start_s"],
                       "raw_score": stretch["peak_score"], "score_definition": "peak linear decision margin",
                       "confidence": None, "rank": rank,
                       "review_priority": "high" if fraction < 1 / 3 else "medium" if fraction < 2 / 3 else "low",
                       "priority_definition": "rank thirds within this model/type, not mental intensity",
                       "evidence": f"Sustained {model.target} classifier score in replayed EEG; cognitive meaning unverified.",
                       "model_version": f"workload-v1-{model.kind}-{model.target}", "overlapping_burst_ids": []})
    return sorted(events, key=lambda e: e["anchor_s"])
