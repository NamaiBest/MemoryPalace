"""Lagged EWMA features for the locked VP003 temporal-feature comparison."""
from collections import Counter
from dataclasses import dataclass
import hashlib

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from scipy.signal import butter, sosfiltfilt

from .signal import prepare
from .workload import (C_GRID, TARGETS, WorkloadModel, export_workload_events,
                       extract_workload_windows, labels_for_times, segment_scores,
                       workload_config, workload_features)

EEG_KINDS = ("power", "power_change", "power_ewma")
KINDS = EEG_KINDS + ("eog_power", "eog_power_ewma")
STEP_S = 0.25
HALFLIFE_S = 2.0
SIGMA_FLOOR = 0.01
WARMUP_STEPS = 8


def ewma_features(log_power):
    """Each row forecasts from earlier differences; NaN rows break history.

    The first emitted row has seven past increments to initialize its forecast,
    and an eighth current increment to score. Updates follow, never precede scoring.
    """
    log_power = np.asarray(log_power, dtype=float)
    if log_power.ndim != 2 or np.isinf(log_power).any():
        raise ValueError("Use a two-dimensional log-power sequence, with NaN for rejected rows.")
    n, dimensions = log_power.shape
    output = np.full((n, 4 * dimensions), np.nan)
    a = 1 - 2 ** (-STEP_S / HALFLIFE_S)
    previous, mean, variance, count = None, None, None, 0
    initial = []
    for i, row in enumerate(log_power):
        if not np.isfinite(row).all():
            previous, mean, variance, count = None, None, None, 0
            initial = []
            continue
        if previous is None:
            previous = row.copy()
            continue
        delta = row - previous
        previous = row.copy()
        count += 1
        if count < WARMUP_STEPS:
            initial.append(delta.copy())
            continue
        if mean is None:
            mean = np.mean(initial, axis=0)
            variance = np.var(initial, axis=0)
        sigma = np.sqrt(np.maximum(variance, SIGMA_FLOOR ** 2))
        innovation = delta - mean
        output[i] = np.concatenate([row, delta, np.log(sigma), innovation / sigma])
        mean = mean + a * innovation
        variance = (1 - a) * (variance + a * innovation ** 2)
    return output


@dataclass
class TemporalFrame:
    recording_id: str
    times: np.ndarray
    raw_valid: np.ndarray
    ready: np.ndarray
    features: dict

    @property
    def evaluation_grid(self):
        # Match the original centers 1, 3, 5, ... seconds even when some are invalid.
        return np.arange(len(self.times)) % round(2 / STEP_S) == 0


def temporal_frame(recording, eye=None):
    config = workload_config()
    epochs, times, accepted = extract_workload_windows(prepare(recording, config), STEP_S)
    power = np.full((len(times), len(config.bands) * len(config.channels)), np.nan)
    if len(accepted):
        power[accepted] = workload_features(epochs, "power")
    temporal = ewma_features(power)
    ready = np.isfinite(temporal).all(axis=1)
    features = {"power": power, "power_change": temporal[:, :2 * power.shape[1]],
                "power_ewma": temporal}
    if eye is not None:
        if eye.shape != (2, recording.samples.shape[1]) or not np.isfinite(eye).all():
            raise ValueError("Eye control requires two finite channels on the same sample clock.")
        filtered = np.stack([sosfiltfilt(butter(4, band, btype="bandpass", fs=200, output="sos"), eye, axis=1)
                             for band in config.bands])
        eye_power = np.full((len(times), 6), np.nan)
        for index in accepted:
            center = round(times[index] * 200)
            eye_power[index] = np.log(np.maximum(filtered[:, :, center - 200:center + 200].var(axis=-1), 1e-12)).ravel()
        eye_temporal = ewma_features(eye_power)
        if not np.array_equal(ready, np.isfinite(eye_temporal).all(axis=1)):
            raise ValueError("Eye/EEG temporal masks differ; all comparisons require identical centers.")
        features.update({"eog_power": eye_power, "eog_power_ewma": eye_temporal})
    return TemporalFrame(recording.recording_id, times, np.isfinite(power).all(axis=1), ready, features)


class TemporalWorkloadModel(WorkloadModel):
    def scan_frame(self, recording, frame):
        self.validate_recording(recording)
        if self.kind.startswith("eog_"):
            raise ValueError("Eye-only controls cannot emit EEG scans or events.")
        if frame.recording_id != recording.recording_id:
            raise ValueError("Feature-frame recording identity mismatch.")
        scores = np.full(len(frame.times), np.nan)
        scores[frame.ready] = self.score_features(recording, frame.features[self.kind][frame.ready])
        return {"times": frame.times, "scores": scores, "valid": frame.ready.copy(),
                "stretches": segment_scores(frame.times, scores)}

    def scan(self, recording):
        """The externally callable path takes only samples and acquisition metadata."""
        self.validate_recording(recording)
        if self.kind.startswith("eog_"):
            raise ValueError("Eye-only controls cannot emit EEG scans or events.")
        return self.scan_frame(recording, temporal_frame(recording))


def validate_calibration(blocks):
    if not blocks or any(b.role != "calibration" for b in blocks):
        raise ValueError("Only calibration blocks may enter temporal-model training.")
    if len({b.recording.session_id for b in blocks}) != 1:
        raise ValueError("Do not pool sessions.")
    identities = {b.recording.processing_id for b in blocks}
    if len(identities) != 1 or "raw" in identities:
        raise ValueError("Require one frozen pre-task ocular calibration.")
    if Counter(b.condition for b in blocks) != Counter({0: 2, 2: 2, 3: 2}):
        raise ValueError("Require two calibration blocks per condition.")
    ordered = sorted(blocks, key=lambda b: b.block_index)
    if any(a.original_offset_s + a.recording.duration_s > b.original_offset_s + 0.005
           for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Calibration excerpts overlap.")
    if any(b.recording.source != "replayed_eeg" for b in ordered):
        raise ValueError("Require replayed real EEG for this experiment.")
    hashes = [hashlib.sha256(b.recording.samples.tobytes()).hexdigest() for b in ordered]
    if len(set(hashes)) != len(hashes) or len({b.recording.recording_id for b in ordered}) != len(ordered):
        raise ValueError("Calibration blocks must be distinct.")
    return ordered, hashes


def quality_counts(block, frame, target):
    labels = labels_for_times(block, frame.times, target)
    use = frame.evaluation_grid & (labels >= 0)
    return {"labeled_windows": int(use.sum()),
            "raw_valid_windows": int((use & frame.raw_valid).sum()),
            "history_ready_windows": int((use & frame.ready).sum()),
            "by_label": {str(label): {
                "labeled": int((use & (labels == label)).sum()),
                "raw_valid": int((use & (labels == label) & frame.raw_valid).sum()),
                "history_ready": int((use & (labels == label) & frame.ready).sum())}
                for label in (0, 1)}}


def fit_temporal_models(blocks):
    blocks, hashes = validate_calibration(blocks)
    frames = [temporal_frame(b.recording, b.eog) for b in blocks]
    models = {}
    for target in TARGETS:
        data = {kind: [] for kind in KINDS}
        labels, groups, repetitions, quality = [], [], [], []
        occurrences = Counter()
        for block, frame in zip(blocks, frames):
            y = labels_for_times(block, frame.times, target)
            use = frame.evaluation_grid & frame.ready & (y >= 0)
            occurrences[block.condition] += 1
            quality.append({"recording_id": block.recording.recording_id, "condition": block.condition,
                            **quality_counts(block, frame, target)})
            if not use.any():
                raise ValueError(f"No usable calibration windows: {quality[-1]}")
            for kind in KINDS:
                data[kind].append(frame.features[kind][use])
            labels.extend(y[use])
            groups.extend([block.block_index] * int(use.sum()))
            repetitions.extend([occurrences[block.condition]] * int(use.sum()))
        y, groups, repetitions = np.asarray(labels), np.asarray(groups), np.asarray(repetitions)
        folds = [(np.flatnonzero(repetitions != r), np.flatnonzero(repetitions == r)) for r in (1, 2)]
        if any(len(np.unique(y[tr])) != 2 or len(np.unique(y[va])) != 2 for tr, va in folds):
            raise ValueError("A calibration fold lacks a class; do not weaken the split.")
        for kind in KINDS:
            X = np.concatenate(data[kind])
            pipeline = Pipeline([("scale", StandardScaler()),
                                 ("linear", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=19))])
            search = GridSearchCV(pipeline, {"linear__C": C_GRID}, cv=folds, scoring="roc_auc",
                                  error_score="raise", n_jobs=1)
            search.fit(X, y)
            card = {"kind": kind, "target": target, "source": "replayed_eeg",
                    "session_id": blocks[0].recording.session_id, "processing_id": blocks[0].recording.processing_id,
                    "training_recordings": [b.recording.recording_id for b in blocks],
                    "training_sample_sha256": hashes, "training_windows": len(y), "positives": int(y.sum()),
                    "quality": quality, "feature_count": X.shape[1],
                    "selected_C": float(search.best_params_["linear__C"]), "C_grid": C_GRID,
                    "selection_cv_auroc": float(search.best_score_), "cv_is_model_selection_only": True,
                    "cv_auroc_by_C": search.cv_results_["mean_test_score"].tolist(),
                    "folds": [{"train_blocks": np.unique(groups[tr]).tolist(), "validation_blocks": np.unique(groups[va]).tolist()}
                              for tr, va in folds],
                    "temporal_features": {"step_s": STEP_S, "halflife_s": HALFLIFE_S,
                                          "sigma_floor": SIGMA_FLOOR, "warmup_steps": WARMUP_STEPS,
                                          "forecast_before_current_update": True, "reset_at_invalid_center": True},
                    "common_history_mask_for_all_models": True,
                    "score": "Uncalibrated margin; same three-second interval rule as the previous experiment.",
                    "limitations": "Task-label proxy; offline filtering; short rest; ocular/sensory/motor confounds."}
            models[(target, kind)] = TemporalWorkloadModel(blocks[0].recording.session_id, kind, target,
                                                          search.best_estimator_, card)
    return models


def export_temporal_events(recording, model, scan, offset_s=0.0):
    if model.kind not in EEG_KINDS:
        raise ValueError("Only EEG temporal models may export EEG events.")
    events = export_workload_events(recording, model, scan, offset_s)
    for event in events:
        event["model_version"] = f"volatility-v1-{model.kind}-{model.target}"
    return events
