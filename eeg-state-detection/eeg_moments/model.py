from dataclasses import asdict, dataclass
import hashlib

import numpy as np
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import __version__
from .signal import Config, StretchReference, gate_mask, make_windows, prepare


def covariances(epochs):
    n, context, bands, channels, samples = epochs.shape
    flat = epochs.reshape(-1, channels, samples)
    flat = flat - flat.mean(axis=-1, keepdims=True)
    result = Covariances(estimator="lwf").transform(flat)
    return result.reshape(n, context, bands, channels, channels)


def power_features(epochs):
    logpower = np.log(np.maximum(epochs.var(axis=-1), 1e-12))
    contrast = logpower[:, 0] - logpower[:, 1:].mean(axis=1)
    return np.concatenate([logpower[:, 0].reshape(len(epochs), -1),
                           contrast.reshape(len(epochs), -1)], axis=1)


class BandTangentFeatures(TransformerMixin, BaseEstimator):
    """One frozen affine-invariant reference per band; context uses the same chart."""

    def fit(self, X, y=None):
        self.maps_ = [TangentSpace(metric="riemann", tsupdate=False).fit(X[:, 0, b])
                      for b in range(X.shape[2])]
        return self

    def transform(self, X):
        features = []
        for b, mapping in enumerate(self.maps_):
            center = mapping.transform(X[:, 0, b])
            surrounding = (mapping.transform(X[:, 1, b]) + mapping.transform(X[:, 2, b])) / 2
            features.extend([center, center - surrounding])
        return np.concatenate(features, axis=1)


def select_calibration(windows, truth, rng):
    centers = np.asarray([b["anchor_s"] for b in truth["bursts"]])
    if len(centers) == 0:
        raise ValueError("Each labeled calibration block needs at least one positive event.")
    distances = np.abs(windows.times[:, None] - centers).min(axis=1)
    positive = np.flatnonzero(distances <= 0.25)
    negative = np.flatnonzero(distances >= 1.5)
    # Keep event/context siblings in their recording group during CV.
    negatives = rng.choice(negative, min(len(negative), max(80, 10 * len(positive))), replace=False)
    hard_negative = []
    for artifact in truth.get("artifacts", []):
        hard_negative.extend(np.flatnonzero((windows.times >= artifact["start_s"] - 1)
                                            & (windows.times <= artifact["end_s"] + 1)
                                            & (distances >= 1.5)))
    indices = np.unique(np.r_[positive, negatives, np.asarray(hard_negative, dtype=int)])
    labels = (distances[indices] <= 0.25).astype(int)
    if len(positive) < 2 or len(np.unique(labels)) != 2:
        raise ValueError("Calibration block lacks clean positive/negative windows.")
    return indices, labels


@dataclass
class EEGModel:
    config: Config
    session_id: str
    source: str
    kind: str
    classifier: Pipeline
    stretch_reference: StretchReference
    model_card: dict

    def scan(self, recording):
        if recording.session_id != self.session_id:
            raise ValueError("New EEG session: recalibration is required; weights do not transfer.")
        if recording.source != self.source:
            raise ValueError("Model provenance differs: synthetic weights cannot score real EEG.")
        if recording.processing_id != self.model_card.get("processing_id", "raw"):
            raise ValueError("Recording preprocessing differs from model calibration.")
        prepared = prepare(recording, self.config)
        windows = make_windows(prepared, self.config)
        if len(windows.times):
            features = covariances(windows.epochs) if self.kind == "tangent" else power_features(windows.epochs)
            scores = self.classifier.decision_function(features)
        else:
            scores = np.empty(0)
        stretches, trace_times, z, trace_valid = self.stretch_reference.detect(prepared, self.config)
        return {"times": windows.times, "scores": scores, "stretches": stretches,
                "trace_times": trace_times, "stretch_z": z, "trace_valid": trace_valid,
                "onset_mask": gate_mask(windows.times, stretches, self.config),
                "rejected_windows": windows.rejected, "total_windows": windows.total,
                "artifact_or_edge_fraction": float(prepared.bad.mean())}

    def detect(self, recording, top_k=5, scope="all", offset_s=0.0, output_session_id=None):
        scan = self.scan(recording)
        mask = scan["onset_mask"] if scope == "onset" else np.ones(len(scan["times"]), dtype=bool)
        if scope not in {"onset", "all"}:
            raise ValueError("Scope must be onset or all.")
        selected = select_events(scan["times"], scan["scores"], mask, self.config, top_k)
        return export_events(recording, self, selected, offset_s, output_session_id,
                             scan["stretches"], scope), scan


def train(calibration, kind="tangent", config=None, seed=19):
    """Calibration is a list of (recording, labels) pairs from independent blocks."""
    if kind not in {"tangent", "power"}:
        raise ValueError("Model kind must be tangent or power.")
    config = config or Config()
    if len(calibration) < 3:
        raise ValueError("At least three independent calibration blocks are required for group CV.")
    sessions = {r.session_id for r, _ in calibration}
    sources = {r.source for r, _ in calibration}
    processing_ids = {r.processing_id for r, _ in calibration}
    ids = [r.recording_id for r, _ in calibration]
    hashes = [hashlib.sha256(r.samples.tobytes()).hexdigest() for r, _ in calibration]
    if len(sessions) != 1 or len(sources) != 1 or len(processing_ids) != 1:
        raise ValueError("Train one session, provenance, and preprocessing identity at a time.")
    if len(set(ids)) != len(ids) or len(set(hashes)) != len(hashes):
        raise ValueError("Calibration blocks must be distinct recordings, not duplicated data.")
    rng = np.random.default_rng(seed)
    prepared_blocks, all_epochs, all_labels, groups = [], [], [], []
    baseline_intervals = []
    for group, (rec, truth) in enumerate(calibration):
        if truth["recording_id"] != rec.recording_id:
            raise ValueError("Calibration label/recording ID mismatch.")
        for event in truth["bursts"]:
            if not 0 <= event["anchor_s"] < rec.duration_s:
                raise ValueError("Calibration event outside recording.")
        prepared = prepare(rec, config)
        prepared_blocks.append(prepared)
        baseline_intervals.append(truth["baseline_intervals_s"])
        windows = make_windows(prepared, config)
        indices, labels = select_calibration(windows, truth, rng)
        all_epochs.append(windows.epochs[indices])
        all_labels.extend(labels)
        groups.extend([group] * len(indices))
    epochs = np.concatenate(all_epochs)
    X = covariances(epochs) if kind == "tangent" else power_features(epochs)
    y = np.asarray(all_labels)
    steps = [("tangent", BandTangentFeatures())] if kind == "tangent" else []
    steps += [("scale", StandardScaler()),
              ("linear", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed))]
    search = GridSearchCV(Pipeline(steps), {"linear__C": [0.01, 0.1, 1.0, 10.0]},
                          cv=GroupKFold(n_splits=3), scoring="average_precision",
                          n_jobs=1, error_score="raise", refit=True)
    search.fit(X, y, groups=np.asarray(groups))
    reference = StretchReference.fit(prepared_blocks, baseline_intervals, config)
    card = {"version": __version__, "kind": kind, "source": next(iter(sources)),
            "processing_id": next(iter(processing_ids)),
            "session_id": next(iter(sessions)), "config": asdict(config),
            "training_recordings": ids, "training_sample_sha256": hashes,
            "training_windows": len(y), "positive_windows": int(y.sum()),
            "selected_C": float(search.best_params_["linear__C"]),
            "selection_cv_average_precision": float(search.best_score_),
            "cv_C_values": [float(p["linear__C"]) for p in search.cv_results_["params"]],
            "cv_average_precision": search.cv_results_["mean_test_score"].tolist(),
            "cv_note": "Grouped calibration model-selection scores, not held-out performance.",
            "stretch_reference": asdict(reference),
            "score": "Uncalibrated linear decision margin; accept >=0 then rank and suppress neighbors.",
            "limitations": ["Oscillatory packet target, no ERP template or P300 claim.",
                            "No cognitive meaning established for a flagged waveform.",
                            "Synthetic calibration cannot transfer to real EEG.",
                            "Offline zero-phase filtering and context limit timing precision."]}
    return EEGModel(config, next(iter(sessions)), next(iter(sources)), kind,
                    search.best_estimator_, reference, card)


def select_events(times, scores, mask, config, top_k=5):
    if top_k < 0:
        raise ValueError("top_k must be nonnegative.")
    selected = []
    if top_k == 0:
        return selected
    eligible = np.flatnonzero(mask & np.isfinite(scores) & (scores >= config.min_score))
    for index in eligible[np.argsort(-scores[eligible], kind="stable")]:
        time = float(times[index])
        if all(abs(time - item["anchor_s"]) >= config.separation_s for item in selected):
            selected.append({"anchor_s": time, "raw_score": float(scores[index])})
            if len(selected) >= top_k:
                break
    return selected


def export_events(recording, model, selected, offset_s=0.0, output_session_id=None,
                  stretches=None, scope="all"):
    """Export independent burst and stretch events; ranks apply within each type."""
    if not np.isfinite(offset_s) or offset_s < 0:
        raise ValueError("Demo offset must be finite and nonnegative.")
    session_id = output_session_id or recording.session_id
    events = []
    for rank, event in enumerate(selected, 1):
        time = event["anchor_s"]
        nearest_onset = (min((s["start_s"] for s in stretches), key=lambda start: abs(start - time))
                         if stretches else None)
        relative_rank = (rank - 1) / max(len(selected), 1)
        priority = "high" if relative_rank < 1 / 3 else "medium" if relative_rank < 2 / 3 else "low"
        key = f"{session_id}:{recording.recording_id}:{model.kind}:{time:.6f}:{offset_s:.6f}"
        events.append({"event_id": "eeg-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                       "session_id": session_id, "recording_id": recording.recording_id,
                       "eeg_session_id": recording.session_id, "source": recording.source,
                       "start_s": max(0, time - model.config.window_s / 2) + offset_s,
                       "end_s": min(recording.duration_s, time + model.config.window_s / 2) + offset_s,
                       "anchor_s": time + offset_s, "eeg_anchor_s": time, "offset_s": offset_s,
                       "search_scope": scope,
                       "within_onset_gate": (abs(time - nearest_onset) <= model.config.gate_radius_s
                                             if nearest_onset is not None else False),
                       "nearest_stretch_onset_s": nearest_onset + offset_s if nearest_onset is not None else None,
                       "offset_from_stretch_onset_s": time - nearest_onset if nearest_onset is not None else None,
                       "signal_type": "burst",
                       "event_type": "synthetic_transient_candidate" if recording.source == "synthetic_eeg"
                       else "eeg_transient_candidate", "raw_score": event["raw_score"],
                       "score_definition": "uncalibrated linear decision margin",
                       "confidence": None, "review_priority": priority,
                       "priority_definition": "rank thirds within signal type, not mental intensity",
                       "rank": rank, "timing_window_s": model.config.window_s,
                       "evidence": f"{model.kind} model flagged an oscillatory candidate in {recording.source}.",
                       "model_version": f"eeg-moments-{__version__}-{model.kind}"})
    ranked_stretches = sorted(stretches or [], key=lambda e: (-e["peak_z"], e["start_s"]))
    for rank, stretch in enumerate(ranked_stretches, 1):
        onset = stretch["start_s"]
        key = f"{session_id}:{recording.recording_id}:stretch:{onset:.6f}:{stretch['end_s']:.6f}:{offset_s:.6f}"
        relative_rank = (rank - 1) / len(ranked_stretches)
        priority = "high" if relative_rank < 1 / 3 else "medium" if relative_rank < 2 / 3 else "low"
        events.append({"event_id": "eeg-stretch-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                       "session_id": session_id, "recording_id": recording.recording_id,
                       "eeg_session_id": recording.session_id, "source": recording.source,
                       "signal_type": "stretch",
                       "event_type": "synthetic_stretch_candidate" if recording.source == "synthetic_eeg"
                       else "eeg_stretch_candidate",
                       "start_s": onset + offset_s, "end_s": stretch["end_s"] + offset_s,
                       "anchor_s": onset + offset_s, "eeg_anchor_s": onset, "offset_s": offset_s,
                       "confirmed_s": stretch["confirmed_s"] + offset_s,
                       "duration_s": stretch["end_s"] - onset,
                       "raw_score": stretch["peak_z"], "score_definition": "peak frontal-band log-power robust z",
                       "confidence": None, "rank": rank, "review_priority": priority,
                       "priority_definition": "rank thirds within signal type, not mental intensity",
                       "evidence": f"Sustained frontal-band power rise in {recording.source}; cognitive meaning unverified.",
                       "model_version": f"eeg-moments-{__version__}-stretch"})
    # Temporal overlap is a navigation link, never corroboration or a merged label.
    burst_events = [e for e in events if e["signal_type"] == "burst"]
    stretch_events = [e for e in events if e["signal_type"] == "stretch"]
    for burst in burst_events:
        burst["overlapping_stretch_ids"] = [s["event_id"] for s in stretch_events
                                            if burst["start_s"] < s["end_s"] and burst["end_s"] > s["start_s"]]
    for stretch in stretch_events:
        stretch["overlapping_burst_ids"] = [b["event_id"] for b in burst_events
                                            if stretch["event_id"] in b["overlapping_stretch_ids"]]
    return sorted(events, key=lambda e: e["anchor_s"])
