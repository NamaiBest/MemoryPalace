from dataclasses import replace

import joblib
import numpy as np
import pytest
from scipy.linalg import block_diag

from eeg_moments.dynamic import (dynamic_frame, estimate_noise, export_dynamic_events,
                                  fit_dynamic_models, temporal_posterior)
from eeg_moments.topology import (barcode_features, epoch_zigzag_features, fit_topological_models,
                                  rips_complex, scan_burst_models, zigzag_barcodes)
from test_workload import example_block

pytest.importorskip("dionysus")


def test_kalman_matches_independent_batch_gaussian_conditioning():
    y = np.array([-0.9, -0.7, 0.4, 1.1, 0.6, 1.3])
    variance, phi, q = 0.8, 0.75, 0.03
    F, H = np.diag([1, phi]), np.ones(2)
    Q = np.diag([q * variance, variance * (1 - phi ** 2)])
    covariance = block_diag(np.diag([4 * variance, variance]), *[Q for _ in y])
    B = np.zeros((2, covariance.shape[0]))
    B[:, :2] = np.eye(2)
    observations = []
    for i in range(len(y)):
        B = F @ B
        B[:, 2 * (i + 1):2 * (i + 2)] += np.eye(2)
        observations.append(H @ B)
    A = np.array(observations)
    Cyy = A @ covariance @ A.T + 0.01 * variance * np.eye(len(y))
    Cxy = B[0] @ covariance @ A.T
    expected_mean = Cxy @ np.linalg.solve(Cyy, y)
    expected_variance = B[0] @ covariance @ B[0] - Cxy @ np.linalg.solve(Cyy, Cxy)
    result = temporal_posterior(y, "dlm", q, {"variance": variance, "phi": phi})
    assert result["scores"][-1] == pytest.approx(expected_mean, abs=1e-12)
    assert result["posterior_sd"][-1] ** 2 == pytest.approx(expected_variance, abs=1e-12)


@pytest.mark.parametrize("method", ["power", "ema", "dlm", "adaptive"])
def test_temporal_inference_resets_at_gaps_and_uses_no_future_scores(method):
    scores = np.r_[np.full(10, -2.0), np.full(10, 3.0)]
    noise = {"variance": 0.5, "phi": 0.9}
    full = temporal_posterior(scores, method, 0.1, noise)
    prefix = temporal_posterior(scores[:12], method, 0.1, noise)
    np.testing.assert_allclose(full["scores"][:12], prefix["scores"])
    gap = temporal_posterior(np.r_[scores, np.nan, scores], method, 0.1, noise)
    assert np.isnan(gap["scores"][20])
    np.testing.assert_allclose(gap["scores"][21:], full["scores"])
    if method in ("dlm", "adaptive"):
        assert np.all(full["posterior_sd"] > 0)
    if method == "adaptive":
        assert np.all((full["change_regime_probability"] >= 0) & (full["change_regime_probability"] <= 1))


def test_identical_switching_regimes_reduce_to_single_kalman_filter():
    y = np.random.default_rng(44).normal(size=30)
    noise = {"variance": 2.0, "phi": 0.5}
    one = temporal_posterior(y, "dlm", 1.0, noise)
    mixture = temporal_posterior(y, "adaptive", 1.0, noise)
    np.testing.assert_allclose(one["scores"], mixture["scores"], atol=1e-12)
    np.testing.assert_allclose(one["posterior_sd"], mixture["posterior_sd"], atol=1e-12)
    np.testing.assert_allclose(mixture["change_regime_probability"], 1 / 11, atol=1e-12)


def test_noise_fit_excludes_unlabeled_gaps_and_class_transitions():
    scores = np.array([0.0, 1.0, -1.0, 1e6, 10.0, 11.0, 9.0])
    labels = np.array([0, 0, 0, -1, 1, 1, 1])
    result = estimate_noise([scores], [labels])
    scores[3] = -1e9
    assert result == estimate_noise([scores], [labels])
    assert result["variance"] == pytest.approx(2 / 3)
    assert result["phi"] == 0


def test_zigzag_tracks_a_loop_birth_and_filling():
    vertices = {(0,), (1,), (2,)}
    path = vertices | {(0, 1), (1, 2)}
    cycle = path | {(0, 2)}
    filled = cycle | {(0, 1, 2)}
    # K0 -> union <- K1 -> union <- K2, with K2 filling the loop.
    bars = zigzag_barcodes([path, cycle, cycle, filled, filled])
    np.testing.assert_array_equal(bars[0], [[0, 5]])
    np.testing.assert_array_equal(bars[1], [[1, 3]])
    descriptor = barcode_features(bars, 5)
    np.testing.assert_array_equal(descriptor[:5], [1, 1, 1, 1, 1])
    np.testing.assert_array_equal(descriptor[10:15], [0, 1, 1, 0, 0])
    assert descriptor[16] == 1  # One H1 interval of length 2 stages.
    d = np.ones((3, 3)) - np.eye(3)
    assert (0, 1, 2) in rips_complex(range(3), d, 1)
    assert len(zigzag_barcodes([filled])[1]) == 0
    with pytest.raises(ValueError, match="faces"):
        zigzag_barcodes([{(0, 1)}])


def test_zigzag_shape_features_are_amplitude_and_channel_order_invariant():
    epoch = np.random.default_rng(192).normal(size=(28, 220))
    features = epoch_zigzag_features(epoch)
    assert features.shape == (108,) and np.isfinite(features).all()
    np.testing.assert_array_equal(epoch_zigzag_features(epoch[::-1] * 7), features)
    assert np.isfinite(epoch_zigzag_features(np.zeros_like(epoch))).all()


def calibration_blocks():
    blocks = [example_block(i, c) for i, c in enumerate((0, 2, 3, 3, 0, 2))]
    for block in blocks:
        block.trials = [{"time_s": 11 + 2 * i, "label": int(i % 3 == 0)} for i in range(20)]
    return blocks


def test_dynamic_calibration_and_saved_inference_contract(tmp_path):
    blocks = calibration_blocks()
    models = fit_dynamic_models(blocks)
    rec = example_block(8, 2, "evaluation").recording
    frame = dynamic_frame(rec)
    for kind in ("power", "ema", "dlm", "adaptive"):
        model = models[kind]
        before = joblib.hash(model)
        scan = model.scan_frame(rec, frame)
        np.testing.assert_array_equal(scan["valid"], frame.valid)
        assert joblib.hash(model) == before
        joblib.dump(model, tmp_path / f"{kind}.joblib")
        restored = joblib.load(tmp_path / f"{kind}.joblib")
        np.testing.assert_allclose(restored.scan_frame(rec, frame)["scores"], scan["scores"], equal_nan=True)
        for event in export_dynamic_events(rec, model, scan, 100):
            assert event["confidence"] is None and event["anchor_s"] == event["eeg_anchor_s"] + 100
        for fold in model.model_card["folds"]:
            assert not set(fold["train_blocks"]) & set(fold["validation_blocks"])
        with pytest.raises(ValueError, match="same calibrated"):
            model.scan_frame(replace(rec, session_id="wrong"), frame)
    with pytest.raises(ValueError, match="Eye-only"):
        models["eog_dlm"].scan_frame(rec, frame)
    with pytest.raises(ValueError, match="Only calibration"):
        fit_dynamic_models([replace(b, role="evaluation") for b in blocks])


def test_topological_models_fit_on_calibration_and_share_scanning_grid(tmp_path):
    models = fit_topological_models(calibration_blocks())
    full = example_block(8, 2, "evaluation").recording
    rec = replace(full, samples=full.samples[:, :2400])  # 12-second smoke scan.
    eeg_models = {k: m for k, m in models.items() if k != "eog_bins"}
    before = {k: joblib.hash(m) for k, m in eeg_models.items()}
    times, scores, rejected = scan_burst_models(rec, eeg_models)
    assert all(len(s) == len(times) and np.isfinite(s).all() for s in scores.values())
    assert rejected >= 0 and len(times) > 0
    for kind, model in eeg_models.items():
        assert joblib.hash(model) == before[kind]
    with pytest.raises(ValueError, match="Eye controls"):
        scan_burst_models(rec, models)
    with pytest.raises(ValueError, match="Only calibration"):
        fit_topological_models([replace(b, role="evaluation") for b in calibration_blocks()])
