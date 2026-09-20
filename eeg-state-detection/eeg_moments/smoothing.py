"""A controlled EMA follow-up using the exact saved band-power classifier."""
from copy import deepcopy
from dataclasses import dataclass

import numpy as np
from sklearn.base import clone

from .dynamic import dynamic_frame, temporal_posterior
from .volatility import validate_calibration
from .workload import export_workload_events, labels_for_times, segment_scores, workload_metrics

HALF_LIVES = (0.5, 1.0, 2.0)


def smooth_scan(scan, half_life_s):
    times = np.asarray(scan["times"])
    scores = np.asarray(scan["scores"])
    valid = np.asarray(scan["valid"])
    if (times.shape != scores.shape or valid.shape != scores.shape
            or not np.array_equal(valid, np.isfinite(scores))
            or (len(times) > 1 and not np.allclose(np.diff(times), 0.25))):
        raise ValueError("Smoothing requires the complete 0.25-second grid and original validity mask.")
    if not np.isfinite(half_life_s) or half_life_s <= 0:
        raise ValueError("Smoothing half-life must be finite and positive.")
    smoothed = temporal_posterior(scores, "ema", half_life_s)["scores"]
    return {"times": times.copy(), "scores": smoothed, "raw_scores": scores.copy(),
            "valid": valid.copy(), "stretches": segment_scores(times, smoothed)}


@dataclass
class SmoothedPowerModel:
    base_model: object
    half_life_s: float
    model_card: dict

    @property
    def session_id(self):
        return self.base_model.session_id

    @property
    def kind(self):
        return "power_ema"

    @property
    def target(self):
        return self.base_model.target

    def validate_recording(self, recording):
        self.base_model.validate_recording(recording)

    def scan(self, recording):
        return smooth_scan(self.base_model.scan(recording), self.half_life_s)


def calibrate_smoothing(blocks, base_model):
    """Select half-life from calibration-only, out-of-fold margin sequences."""
    blocks, hashes = validate_calibration(blocks)
    if base_model.kind != "power" or base_model.target != "task_rest":
        raise ValueError("Use the original power/task_rest model.")
    if (hashes != base_model.model_card["training_sample_sha256"] or
            [b.recording.recording_id for b in blocks] != base_model.model_card["training_recordings"]):
        raise ValueError("Smoothing calibration must match the base classifier's original training blocks.")
    for block in blocks:
        base_model.validate_recording(block.recording)
    frames = [dynamic_frame(b.recording) for b in blocks]
    ys = [labels_for_times(b, f.times, "task_rest") for b, f in zip(blocks, frames)]
    lookup = {b.block_index: i for i, b in enumerate(blocks)}
    folds = base_model.model_card["folds"]
    rows = {half: [] for half in HALF_LIVES}
    for fold in folds:
        train = [lookup[i] for i in fold["train_blocks"]]
        validation = [lookup[i] for i in fold["validation_blocks"]]
        if set(train) & set(validation) or set(train) | set(validation) != set(range(len(blocks))):
            raise ValueError("Calibration folds must partition all blocks without overlap.")
        X, labels = [], []
        for i in train:
            use = frames[i].valid & frames[i].evaluation_grid & (ys[i] >= 0)
            X.append(frames[i].features["eeg"][use])
            labels.extend(ys[i][use])
        if len(np.unique(labels)) != 2:
            raise ValueError("Smoothing calibration fold lacks a class.")
        temporary = clone(base_model.classifier).fit(np.concatenate(X), labels)
        truth, predictions = [], {half: [] for half in HALF_LIVES}
        for i in validation:
            frame = frames[i]
            margins = np.full(len(frame.times), np.nan)
            if frame.valid.any():
                margins[frame.valid] = temporary.decision_function(frame.features["eeg"][frame.valid])
            use = frame.valid & frame.evaluation_grid & (ys[i] >= 0)
            truth.extend(ys[i][use])
            for half in HALF_LIVES:
                predictions[half].extend(temporal_posterior(margins, "ema", half)["scores"][use])
        for half in HALF_LIVES:
            metrics = workload_metrics(truth, predictions[half])
            if metrics["balanced_accuracy"] is None:
                raise ValueError("Smoothing validation fold lacks a class.")
            rows[half].append(metrics)
    candidates = [{"half_life_s": half,
                   "mean_balanced_accuracy": float(np.mean([r["balanced_accuracy"] for r in rows[half]])),
                   "mean_auroc": float(np.mean([r["auroc"] for r in rows[half]])),
                   "fold_metrics": rows[half]} for half in HALF_LIVES]
    best = max(candidates, key=lambda row: (row["mean_balanced_accuracy"], row["mean_auroc"], -row["half_life_s"]))
    card = deepcopy(base_model.model_card)
    card.update({"kind": "power_ema", "base_classifier_weights_unchanged": True,
                 "half_life_s": best["half_life_s"], "smoothing_candidates": candidates,
                 "selection": "Calibration out-of-fold balanced accuracy, then AUROC, then shorter half-life; original C fixed",
                 "score": "Exponentially smoothed original linear decision margin; not mental-state confidence"})
    return SmoothedPowerModel(base_model, best["half_life_s"], card)


def export_smoothed_events(recording, model, scan, offset_s=0.0):
    events = export_workload_events(recording, model, scan, offset_s)
    for event in events:
        event["model_version"] = f"smoothing-v1-power-{model.half_life_s:g}s"
        event["score_definition"] = "peak exponentially smoothed linear decision margin"
    return events
