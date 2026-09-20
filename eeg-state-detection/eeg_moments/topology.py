"""Actual zigzag H0/H1 descriptors of short multichannel EEG trajectories."""
from itertools import combinations

import numpy as np
from scipy.signal import resample_poly
from scipy.spatial.distance import pdist, squareform
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .erp import ERPMeanBins, ERPModel, erp_config, extract_epochs, eog_epochs
from .signal import prepare
from .volatility import validate_calibration

BURST_KINDS = ("mean_bins", "zigzag", "mean_bins_zigzag", "eog_bins")
RADII = (0.75, 1.0, 1.25)
C_GRID = [0.001, 0.01, 0.1, 1.0, 10.0]


def rips_complex(vertices, distances, radius):
    """Vietoris–Rips 2-skeleton: include filled triangles, not just graph cycles."""
    vertices = sorted(vertices)
    simplices = {(v,) for v in vertices}
    edges = {(a, b) for a, b in combinations(vertices, 2) if distances[a, b] <= radius}
    simplices.update(edges)
    simplices.update((a, b, c) for a, b, c in combinations(vertices, 3)
                     if (a, b) in edges and (a, c) in edges and (b, c) in edges)
    return simplices


def zigzag_barcodes(complexes):
    """Encode simplex additions/deletions; interval coordinates are stage indices."""
    import dionysus as d

    if not complexes:
        raise ValueError("A nonempty zigzag is required.")
    for complex_ in complexes:
        for simplex in complex_:
            if len(simplex) > 1 and any(face not in complex_ for face in combinations(simplex, len(simplex) - 1)):
                raise ValueError("Every simplex must include all its faces.")
    simplices = sorted(set().union(*complexes), key=lambda s: (len(s), s))
    if not simplices:
        return [np.empty((0, 2)), np.empty((0, 2))]
    times = []
    for simplex in simplices:
        membership = np.array([False] + [simplex in c for c in complexes] + [False], dtype=int)
        times.append(np.flatnonzero(np.diff(membership)).astype(float).tolist())
    _, diagrams, _ = d.zigzag_homology_persistence(d.Filtration(simplices), times)
    return [np.array([(p.birth, p.death) for p in diagrams[dimension] if p.death > p.birth], dtype=float).reshape(-1, 2)
            if dimension < len(diagrams) else np.empty((0, 2)) for dimension in (0, 1)]


def barcode_features(barcodes, n_stages):
    features = []
    for bars in barcodes:
        if not np.isfinite(bars).all():
            raise ValueError("Close terminal zigzag intervals before computing features.")
        counts = [np.sum((bars[:, 0] <= t) & (bars[:, 1] > t)) for t in np.arange(n_stages) + 0.25]
        lifetimes = np.rint(bars[:, 1] - bars[:, 0]).astype(int)
        histogram = np.bincount(lifetimes, minlength=n_stages + 1)[1:n_stages + 1]
        features.extend(counts)
        features.extend(histogram)
    return np.array(features, dtype=float)


def epoch_zigzag_features(epoch):
    if epoch.shape != (28, 220) or not np.isfinite(epoch).all():
        raise ValueError("Zigzag input must be a finite 28-channel, 220-sample ERP epoch.")
    points = resample_poly(epoch, 1, 8, axis=1).T
    distances = squareform(pdist(points))
    positive = distances[np.triu_indices(len(points), 1)]
    positive = positive[positive > 1e-12]
    distances /= np.median(positive) if len(positive) else 1.0
    clouds = [set(range(start, start + 8)) for start in (0, 5, 10, 15, 20)]
    features = []
    for radius in RADII:
        complexes = []
        for i, cloud in enumerate(clouds):
            if i:
                complexes.append(rips_complex(clouds[i - 1] | cloud, distances, radius))
            complexes.append(rips_complex(cloud, distances, radius))
        features.extend(barcode_features(zigzag_barcodes(complexes), len(complexes)))
    return np.asarray(features)


def burst_feature_bank(epochs):
    bins = ERPMeanBins().transform(epochs) if len(epochs) else np.empty((0, 140))
    zigzag = np.stack([epoch_zigzag_features(epoch) for epoch in epochs]) if len(epochs) else np.empty((0, 108))
    return {"mean_bins": bins, "zigzag": zigzag, "mean_bins_zigzag": np.concatenate([bins, zigzag], axis=1)}


class TopologicalERPModel(ERPModel):
    def score_features(self, recording, features):
        self.validate_recording(recording)
        return self.classifier.decision_function(features) if len(features) else np.empty(0)

    def score(self, recording, epochs):
        if self.kind in ("mean_bins", "eog_bins"):
            features = ERPMeanBins().transform(epochs) if len(epochs) else []
        else:
            features = burst_feature_bank(epochs)[self.kind]
        return self.score_features(recording, features)


def fit_topological_models(blocks):
    blocks, hashes = validate_calibration(blocks)
    data = {kind: [] for kind in BURST_KINDS}
    labels, groups, quality = [], [], []
    for block in blocks:
        if block.condition not in (2, 3):
            continue
        times = np.array([t["time_s"] for t in block.trials])
        epochs, valid = extract_epochs(prepare(block.recording, erp_config()), times)
        y = np.array([t["label"] for t in block.trials])[valid]
        bank = burst_feature_bank(epochs)
        eye = eog_epochs(block, times[valid])
        bank["eog_bins"] = ERPMeanBins().transform(eye) if len(eye) else np.empty((0, 10))
        for kind in BURST_KINDS:
            data[kind].append(bank[kind])
        labels.extend(y)
        groups.extend([block.block_index] * len(y))
        quality.append({"recording_id": block.recording.recording_id, "accepted": len(y),
                        "targets": int(y.sum()), "total": len(times)})
    y, groups = np.asarray(labels), np.asarray(groups)
    if len(y) < 12 or len(np.unique(y)) != 2:
        raise ValueError("Insufficient usable ERP calibration trials.")
    folds = list(StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=19).split(np.zeros(len(y)), y, groups))
    if any(len(np.unique(y[tr])) != 2 or len(np.unique(y[va])) != 2 for tr, va in folds):
        raise ValueError("ERP calibration folds lack a class.")
    models = {}
    for kind in BURST_KINDS:
        X = np.concatenate(data[kind])
        search = GridSearchCV(Pipeline([("scale", StandardScaler()), ("linear", LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=19))]),
            {"linear__C": C_GRID}, cv=folds, scoring="average_precision", error_score="raise", n_jobs=1).fit(X, y)
        card = {"kind": kind, "source": "replayed_eeg", "session_id": blocks[0].recording.session_id,
                "processing_id": blocks[0].recording.processing_id,
                "training_recordings": [b.recording.recording_id for b in blocks],
                "training_sample_sha256": hashes, "training_hashes": hashes,
                "selected_C": float(search.best_params_["linear__C"]), "C_grid": C_GRID,
                "calibration_cv_average_precision": float(search.best_score_), "quality": quality,
                "training_trials": len(y), "training_targets": int(y.sum()), "features": X.shape[1],
                "folds": [{"train_blocks": np.unique(groups[tr]).tolist(), "validation_blocks": np.unique(groups[va]).tolist()}
                          for tr, va in folds],
                "zigzag": {"radii": list(RADII), "coefficient_field": 2, "dimensions": [0, 1],
                           "trajectory_sample_rate": 25, "cloud_size": 8, "stages": 9,
                           "features": "Betti counts + stage-lifetime histograms; per-epoch median-distance normalization"},
                "interpretation": "Target/non-target proxy, not spontaneous cognitive events or measured single-trial P300 truth."}
        models[kind] = TopologicalERPModel(blocks[0].recording.session_id, kind, search.best_estimator_, card)
    return models


def scan_burst_models(recording, models):
    """Shared marker-free windows and features, without repeated topology work."""
    for kind, model in models.items():
        model.validate_recording(recording)
        if kind == "eog_bins":
            raise ValueError("Eye controls cannot scan EEG.")
    times = np.arange(0.1, recording.duration_s - 1.0, 0.1)
    epochs, valid = extract_epochs(prepare(recording, erp_config()), times)
    bank = burst_feature_bank(epochs)
    return times[valid], {kind: model.score_features(recording, bank[kind]) for kind, model in models.items()}, len(times) - len(valid)
