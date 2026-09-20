"""Sliding Hann-window Fourier power features for a locked workload comparison."""
from collections import Counter
from dataclasses import dataclass, replace
from types import SimpleNamespace

import numpy as np
from scipy.signal import butter, get_window, sosfiltfilt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .signal import prepare
from .volatility import validate_calibration
from .workload import (TARGETS, WorkloadModel, export_workload_events, extract_workload_windows,
                       eye_windows, labels_for_times, segment_scores, workload_config, workload_features)

EEG_KINDS = ("power", "fft_bands", "fft_bins")
KINDS = EEG_KINDS + ("eog_power", "eog_fft_bands", "eog_fft_bins")
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
FINE_BANDS = tuple((float(f), float(f + 1)) for f in range(4, 30))


def fourier_psd(epochs, sample_rate=200.0):
    """Real, one-sided PSD in uV²/Hz; two-second input, no zero padding."""
    epochs = np.asarray(epochs, dtype=float)
    if epochs.ndim != 3 or epochs.shape[-1] != round(2 * sample_rate) or not np.isfinite(epochs).all():
        raise ValueError("FFT input must be finite windows x channels x two seconds of samples.")
    width = epochs.shape[-1]
    taper = get_window("hann", width, fftbins=True)
    centered = epochs - epochs.mean(axis=-1, keepdims=True)
    coefficients = np.fft.rfft(centered * taper, axis=-1)
    density = np.abs(coefficients) ** 2 / (sample_rate * np.sum(taper ** 2))
    density[..., 1:-1 if width % 2 == 0 else None] *= 2
    return np.fft.rfftfreq(width, 1 / sample_rate), density


def spectral_features(frequencies, density, bands):
    df = frequencies[1] - frequencies[0]
    powers = np.stack([density[..., (frequencies >= lo) & (frequencies < hi)].sum(axis=-1) * df
                       for lo, hi in bands], axis=1)
    return np.log(np.maximum(powers, 1e-12)).reshape(len(density), len(bands) * density.shape[1])


@dataclass
class SpectralFrame:
    recording_id: str
    times: np.ndarray
    valid: np.ndarray
    features: dict

    @property
    def evaluation_grid(self):
        return np.arange(len(self.times)) % 8 == 0


def spectral_frame(recording, eye=None):
    config = workload_config()
    prepared = prepare(recording, config)
    broad = prepare(recording, replace(config, bands=((1.0, 40.0),)))
    if not np.array_equal(prepared.bad, broad.bad):
        raise ValueError("Broadband and reference quality masks differ.")
    epochs, times, accepted = extract_workload_windows(prepared, 0.25)
    fft_epochs, fft_times, fft_accepted = extract_workload_windows(broad, 0.25)
    if not np.array_equal(times, fft_times) or not np.array_equal(accepted, fft_accepted):
        raise ValueError("FFT and reference windows must match exactly.")
    features = {"power": np.full((len(times), 84), np.nan),
                "fft_bands": np.full((len(times), 84), np.nan),
                "fft_bins": np.full((len(times), 728), np.nan)}
    if len(accepted):
        features["power"][accepted] = workload_features(epochs, "power")
        frequencies, density = fourier_psd(fft_epochs[:, 0])
        features["fft_bands"][accepted] = spectral_features(frequencies, density, config.bands)
        features["fft_bins"][accepted] = spectral_features(frequencies, density, FINE_BANDS)
    if eye is not None:
        if eye.shape != (2, recording.samples.shape[1]) or not np.isfinite(eye).all():
            raise ValueError("Eye channels must be finite and share the EEG clock.")
        for kind, count in (("eog_power", 6), ("eog_fft_bands", 6), ("eog_fft_bins", 52)):
            features[kind] = np.full((len(times), count), np.nan)
        if len(accepted):
            # Same fixed filters as the reference eye control, at EEG-accepted centers.
            proxy = SimpleNamespace(eog=eye)
            features["eog_power"][accepted] = workload_features(eye_windows(proxy, times[accepted]), "eog_power")
            eye_broad = sosfiltfilt(butter(4, [1, 40], btype="bandpass", fs=200, output="sos"), eye, axis=1)
            eye_epochs = np.stack([eye_broad[:, round(t * 200) - 200:round(t * 200) + 200] for t in times[accepted]])
            frequencies, density = fourier_psd(eye_epochs)
            features["eog_fft_bands"][accepted] = spectral_features(frequencies, density, config.bands)
            features["eog_fft_bins"][accepted] = spectral_features(frequencies, density, FINE_BANDS)
    valid = np.zeros(len(times), dtype=bool)
    valid[accepted] = True
    if any(not np.array_equal(valid, np.isfinite(x).all(axis=1)) for x in features.values()):
        raise ValueError("All feature models must share the same valid windows.")
    return SpectralFrame(recording.recording_id, times, valid, features)


class FourierWorkloadModel(WorkloadModel):
    def scan_frame(self, recording, frame):
        self.validate_recording(recording)
        if self.kind not in EEG_KINDS:
            raise ValueError("Eye-only models cannot scan EEG or export EEG events.")
        if recording.recording_id != frame.recording_id:
            raise ValueError("Feature-frame identity mismatch.")
        scores = np.full(len(frame.times), np.nan)
        scores[frame.valid] = self.score_features(recording, frame.features[self.kind][frame.valid])
        return {"times": frame.times, "scores": scores, "valid": frame.valid.copy(),
                "stretches": segment_scores(frame.times, scores)}

    def scan(self, recording):
        self.validate_recording(recording)
        if self.kind not in EEG_KINDS:
            raise ValueError("Eye-only models cannot scan EEG or export EEG events.")
        return self.scan_frame(recording, spectral_frame(recording))


def quality_counts(block, frame, target):
    labels = labels_for_times(block, frame.times, target)
    selected = frame.evaluation_grid & (labels >= 0)
    return {"labeled_windows": int(selected.sum()), "accepted_windows": int((selected & frame.valid).sum()),
            "by_label": {str(label): {"labeled": int((selected & (labels == label)).sum()),
                                      "accepted": int((selected & frame.valid & (labels == label)).sum())}
                         for label in (0, 1)}}


def fit_fourier_models(blocks):
    blocks, hashes = validate_calibration(blocks)
    frames = [spectral_frame(b.recording, b.eog) for b in blocks]
    models = {}
    for target in TARGETS:
        features, labels, groups, repetitions, quality = {kind: [] for kind in KINDS}, [], [], [], []
        occurrences = Counter()
        for block, frame in zip(blocks, frames):
            y = labels_for_times(block, frame.times, target)
            use = frame.evaluation_grid & frame.valid & (y >= 0)
            occurrences[block.condition] += 1
            quality.append({"recording_id": block.recording.recording_id, "condition": block.condition,
                            **quality_counts(block, frame, target)})
            if not use.any():
                raise ValueError(f"No clean calibration windows: {quality[-1]}")
            for kind in KINDS:
                features[kind].append(frame.features[kind][use])
            labels.extend(y[use])
            groups.extend([block.block_index] * int(use.sum()))
            repetitions.extend([occurrences[block.condition]] * int(use.sum()))
        y, groups, repetitions = np.asarray(labels), np.asarray(groups), np.asarray(repetitions)
        folds = [(np.flatnonzero(repetitions != r), np.flatnonzero(repetitions == r)) for r in (1, 2)]
        if any(len(np.unique(y[tr])) != 2 or len(np.unique(y[va])) != 2 for tr, va in folds):
            raise ValueError("A calibration fold lacks a class; do not weaken the split.")
        for kind in KINDS:
            X = np.concatenate(features[kind])
            pipeline = Pipeline([("scale", StandardScaler()),
                                 ("linear", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=19))])
            search = GridSearchCV(pipeline, {"linear__C": C_VALUES}, cv=folds, scoring="roc_auc",
                                  error_score="raise", n_jobs=1)
            search.fit(X, y)
            card = {"kind": kind, "target": target, "source": "replayed_eeg",
                    "session_id": blocks[0].recording.session_id, "processing_id": blocks[0].recording.processing_id,
                    "training_recordings": [b.recording.recording_id for b in blocks],
                    "training_sample_sha256": hashes, "training_windows": len(y), "positives": int(y.sum()),
                    "feature_count": X.shape[1], "quality": quality, "selected_C": float(search.best_params_["linear__C"]),
                    "C_grid": C_VALUES, "selection_cv_auroc": float(search.best_score_),
                    "cv_auroc_by_C": search.cv_results_["mean_test_score"].tolist(), "cv_is_model_selection_only": True,
                    "folds": [{"train_blocks": np.unique(groups[tr]).tolist(), "validation_blocks": np.unique(groups[va]).tolist()}
                              for tr, va in folds],
                    "representation": "filtered band variance" if kind in ("power", "eog_power") else "windowed Fourier PSD",
                    "spectrum": {"sample_rate": 200, "window_s": 2, "hop_s": 0.25,
                                 "fft_samples": 400, "window": "periodic Hann", "detrend": "window mean",
                                 "broad_filter_hz": [1, 40], "density_units": "uV^2/Hz",
                                 "fine_bands_hz": FINE_BANDS, "power_floor_uv2": 1e-12,
                                 "feature_order": "band-major then channel; natural log integrated power"}
                                 if kind not in ("power", "eog_power") else None,
                    "score": "Uncalibrated margin, same nonnegative-for-three-seconds segmentation.",
                    "limitations": "Task proxies, short rest, offline filtering, one participant and ocular/motor/sensory confounds."}
            models[(target, kind)] = FourierWorkloadModel(blocks[0].recording.session_id, kind, target,
                                                         search.best_estimator_, card)
    return models


def export_fourier_events(recording, model, scan, offset_s=0.0):
    if model.kind not in EEG_KINDS:
        raise ValueError("Only EEG Fourier-comparison models may export EEG events.")
    events = export_workload_events(recording, model, scan, offset_s)
    for event in events:
        event["model_version"] = f"fourier-v1-{model.kind}-{model.target}"
    return events
