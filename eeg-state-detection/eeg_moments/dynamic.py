"""Calibration-selected Bayesian temporal inference on workload margins."""
from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .signal import prepare
from .volatility import validate_calibration
from .workload import (C_GRID, WorkloadModel, export_workload_events, extract_workload_windows,
                       eye_windows, labels_for_times, segment_scores, workload_config,
                       workload_features, workload_metrics)

METHODS = ("power", "ema", "dlm", "adaptive")
KINDS = METHODS + tuple("eog_" + m for m in METHODS)
SETTINGS = {"power": [0.0], "ema": [0.5, 1.0, 2.0],
            "dlm": [0.001, 0.01, 0.1], "adaptive": [0.001, 0.01, 0.1]}
TRANSITION = np.array([[0.98, 0.02], [0.20, 0.80]])


@dataclass
class DynamicFrame:
    recording_id: str
    times: np.ndarray
    valid: np.ndarray
    features: dict

    @property
    def evaluation_grid(self):
        return np.arange(len(self.times)) % 8 == 0


def dynamic_frame(recording, eye_block=None):
    epochs, times, accepted = extract_workload_windows(prepare(recording, workload_config()), 0.25)
    features = {"eeg": np.full((len(times), 84), np.nan)}
    if len(epochs):
        features["eeg"][accepted] = workload_features(epochs, "power")
    if eye_block is not None:
        if eye_block.recording.recording_id != recording.recording_id:
            raise ValueError("Eye/EEG recording mismatch.")
        features["eog"] = np.full((len(times), 6), np.nan)
        if len(accepted):
            features["eog"][accepted] = workload_features(eye_windows(eye_block, times[accepted]), "eog_power")
    return DynamicFrame(recording.recording_id, times, np.isfinite(features["eeg"]).all(axis=1), features)


def estimate_noise(score_rows, label_rows):
    """Within-class residual AR(1), using calibration training blocks only."""
    pooled = {c: np.concatenate([s[(y == c) & np.isfinite(s)] for s, y in zip(score_rows, label_rows)])
              for c in (0, 1)}
    if any(not len(v) for v in pooled.values()):
        raise ValueError("Noise estimation requires both labeled calibration classes.")
    means = {c: float(v.mean()) for c, v in pooled.items()}
    residuals, numerator, denominator = [], 0.0, 0.0
    for scores, labels in zip(score_rows, label_rows):
        valid = np.isfinite(scores) & (labels >= 0)
        r = np.full(len(scores), np.nan)
        r[valid] = scores[valid] - np.array([means[int(c)] for c in labels[valid]])
        residuals.extend(r[valid])
        pairs = valid[1:] & valid[:-1] & (labels[1:] == labels[:-1])
        numerator += float(np.dot(r[:-1][pairs], r[1:][pairs]))
        denominator += float(np.dot(r[:-1][pairs], r[:-1][pairs]))
    return {"variance": max(float(np.mean(np.square(residuals))), 1e-4),
            "phi": float(np.clip(numerator / max(denominator, 1e-12), 0, 0.98))}


def kalman_update(mean, covariance, observation, q, variance, phi):
    """Two-state level + AR(1) error, with scalar noisy observation [1, 1]."""
    F = np.diag([1.0, phi])
    Q = np.diag([q * variance, variance * (1 - phi ** 2)])
    predicted = F @ mean
    P = F @ covariance @ F.T + Q
    H = np.ones(2)
    innovation = observation - H @ predicted
    S = float(H @ P @ H + 0.01 * variance)
    gain = P @ H / S
    updated = predicted + gain * innovation
    # Joseph form retains symmetry/positive semidefiniteness under roundoff.
    A = np.eye(2) - np.outer(gain, H)
    posterior = A @ P @ A.T + 0.01 * variance * np.outer(gain, gain)
    log_likelihood = -0.5 * (np.log(2 * np.pi * S) + innovation ** 2 / S)
    return updated, posterior, float(log_likelihood)


def temporal_posterior(scores, method, setting=0.01, noise=None):
    """Causal state inference; rejected rows reset history and remain NaN.

    EEG filtering/windows remain offline. Reported uncertainty is conditional on
    fitted noise parameters; adaptive uses IMM Gaussian moment approximations.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1 or np.isinf(scores).any() or method not in METHODS:
        raise ValueError("Expected one margin sequence with NaN gaps and a known method.")
    output = {key: np.full(len(scores), np.nan) for key in ("scores", "posterior_sd", "change_regime_probability")}
    if method == "power":
        output["scores"] = scores.copy()
        return output
    if setting <= 0:
        raise ValueError("Temporal setting must be positive.")
    if method in ("dlm", "adaptive"):
        variance, phi = noise["variance"], noise["phi"]
        if not variance > 0 or not 0 <= phi < 1:
            raise ValueError("Invalid observation-noise model.")
    state = None
    for i, value in enumerate(scores):
        if not np.isfinite(value):
            state = None
            continue
        if method == "ema":
            alpha = 1 - 2 ** (-0.25 / setting)
            state = value if state is None else state + alpha * (value - state)
            output["scores"][i] = state
            continue
        if method == "dlm":
            if state is None:
                state = (np.zeros(2), np.diag([4 * variance, variance]))
            mean, P, _ = kalman_update(*state, value, setting, variance, phi)
            state = mean, P
            output["scores"][i], output["posterior_sd"][i] = mean[0], np.sqrt(max(P[0, 0], 0))
            continue
        if state is None:
            state = (np.zeros((2, 2)), np.array([np.diag([4 * variance, variance])] * 2),
                     np.array([10 / 11, 1 / 11]))
        means, covariances, weights = state
        prior_weights = weights @ TRANSITION
        new_means, new_covariances, log_weights = [], [], []
        for j, q in enumerate((setting, 1.0)):
            mixing = weights * TRANSITION[:, j] / prior_weights[j]
            mixed_mean = mixing @ means
            differences = means - mixed_mean
            mixed_covariance = sum(w * (P + np.outer(delta, delta))
                                   for w, P, delta in zip(mixing, covariances, differences))
            mean, P, ll = kalman_update(mixed_mean, mixed_covariance, value, q, variance, phi)
            new_means.append(mean)
            new_covariances.append(P)
            log_weights.append(np.log(prior_weights[j]) + ll)
        weights = np.exp(log_weights - logsumexp(log_weights))
        means, covariances = np.array(new_means), np.array(new_covariances)
        level = weights @ means[:, 0]
        level_variance = weights @ (covariances[:, 0, 0] + (means[:, 0] - level) ** 2)
        output["scores"][i] = level
        output["posterior_sd"][i] = np.sqrt(max(level_variance, 0))
        output["change_regime_probability"][i] = weights[1]
        state = means, covariances, weights
    return output


class DynamicWorkloadModel(WorkloadModel):
    def scan_frame(self, recording, frame, allow_eye_control=False):
        self.validate_recording(recording)
        eye = self.kind.startswith("eog_")
        if eye and not allow_eye_control:
            raise ValueError("Eye-only controls cannot export EEG scans.")
        if frame.recording_id != recording.recording_id:
            raise ValueError("Feature-frame recording mismatch.")
        scores = np.full(len(frame.times), np.nan)
        if frame.valid.any():
            scores[frame.valid] = self.classifier.decision_function(frame.features["eog" if eye else "eeg"][frame.valid])
        posterior = temporal_posterior(scores, self.kind.removeprefix("eog_"),
                                       self.model_card["temporal_setting"], self.model_card["noise"])
        return {"times": frame.times, "valid": frame.valid.copy(), "raw_scores": scores, **posterior,
                "stretches": segment_scores(frame.times, posterior["scores"])}

    def scan(self, recording):
        return self.scan_frame(recording, dynamic_frame(recording))


def fit_dynamic_models(blocks):
    blocks, hashes = validate_calibration(blocks)
    frames = [dynamic_frame(b.recording, b) for b in blocks]
    labels = [labels_for_times(b, f.times, "task_rest") for b, f in zip(blocks, frames)]
    counts, repetition = Counter(), []
    for block in blocks:
        counts[block.condition] += 1
        repetition.append(counts[block.condition])
    folds = [(np.flatnonzero(np.array(repetition) != r), np.flatnonzero(np.array(repetition) == r)) for r in (1, 2)]

    def fit_classifier(indices, feature_key, c):
        X, y = [], []
        for i in indices:
            use = frames[i].valid & frames[i].evaluation_grid & (labels[i] >= 0)
            X.append(frames[i].features[feature_key][use])
            y.extend(labels[i][use])
        if len(np.unique(y)) != 2:
            raise ValueError("Calibration classifier lacks a class.")
        clf = Pipeline([("scale", StandardScaler()), ("linear", LogisticRegression(
            C=c, class_weight="balanced", max_iter=2000, random_state=19))]).fit(np.concatenate(X), y)
        rows = []
        for frame in frames:
            scores = np.full(len(frame.times), np.nan)
            if frame.valid.any():
                scores[frame.valid] = clf.decision_function(frame.features[feature_key][frame.valid])
            rows.append(scores)
        noise = estimate_noise([rows[i] for i in indices], [labels[i] for i in indices])
        return clf, noise, rows

    models = {}
    for feature_key, prefix in (("eeg", ""), ("eog", "eog_")):
        candidates = {method: [] for method in METHODS}
        for c in C_GRID:
            fitted_folds = [fit_classifier(tr, feature_key, c) for tr, _ in folds]
            for method in METHODS:
                for setting in SETTINGS[method]:
                    metrics = []
                    for (_, va), (_, noise, rows) in zip(folds, fitted_folds):
                        ys, ss = [], []
                        for i in va:
                            posterior = temporal_posterior(rows[i], method, setting, noise)
                            use = frames[i].valid & frames[i].evaluation_grid & (labels[i] >= 0)
                            ys.extend(labels[i][use])
                            ss.extend(posterior["scores"][use])
                        m = workload_metrics(ys, ss)
                        if m["balanced_accuracy"] is None:
                            raise ValueError("Calibration validation fold lacks a class.")
                        metrics.append(m)
                    candidates[method].append({"C": c, "setting": setting,
                        "balanced_accuracy": float(np.mean([m["balanced_accuracy"] for m in metrics])),
                        "auroc": float(np.mean([m["auroc"] for m in metrics]))})
        for method in METHODS:
            best = max(candidates[method], key=lambda m: (m["balanced_accuracy"], m["auroc"], -m["C"], -m["setting"]))
            classifier, noise, _ = fit_classifier(range(len(blocks)), feature_key, best["C"])
            kind = prefix + method
            card = {"kind": kind, "target": "task_rest", "source": "replayed_eeg",
                    "session_id": blocks[0].recording.session_id,
                    "processing_id": blocks[0].recording.processing_id,
                    "training_recordings": [b.recording.recording_id for b in blocks],
                    "training_sample_sha256": hashes, "selected_C": best["C"],
                    "temporal_setting": best["setting"], "noise": noise,
                    "calibration_candidates": candidates[method], "selection": "balanced accuracy, then AUROC",
                    "folds": [{"train_blocks": [blocks[i].block_index for i in tr],
                               "validation_blocks": [blocks[i].block_index for i in va]} for tr, va in folds],
                    "adaptive_transition_matrix": TRANSITION.tolist() if method == "adaptive" else None,
                    "uncertainty": "Conditional on plug-in parameters; adaptive uses IMM approximation; not cognitive-state confidence.",
                    "interpretation": "Task/rest proxy; same-session calibration; no spontaneous-event claim."}
            models[kind] = DynamicWorkloadModel(blocks[0].recording.session_id, kind, "task_rest", classifier, card)
    return models


def export_dynamic_events(recording, model, scan, offset_s=0.0):
    events = export_workload_events(recording, model, scan, offset_s)
    for event in events:
        event["model_version"] = f"dynamic-v1-{model.kind}"
        event["score_definition"] = "peak temporal estimate of task/rest margin; uncalibrated"
    return events
