from dataclasses import replace

import joblib
import numpy as np
import pytest

from eeg_moments.signal import prepare
from eeg_moments.volatility import (HALFLIFE_S, SIGMA_FLOOR, STEP_S, ewma_features,
                                    export_temporal_events, fit_temporal_models,
                                    quality_counts, temporal_frame)
from eeg_moments.workload import extract_workload_windows, workload_config, workload_features
from eeg_moments.workload_benchmark import assert_heldout
from test_workload import example_block


def test_ewma_matches_independent_weighted_moments():
    increments = np.arange(1, 21, dtype=float)
    sequence = np.r_[0.0, np.cumsum(increments)][:, None]
    output = ewma_features(sequence)
    assert np.isnan(output[:8]).all()
    a = 1 - 2 ** (-STEP_S / HALFLIFE_S)
    for index in range(8, len(sequence)):
        # Build all historical weights explicitly; do not repeat the implementation's
        # recursive centered-variance formula. Current increment is deliberately absent.
        added = index - 8
        weights = np.r_[np.full(7, (1-a) ** added / 7),
                        [a * (1-a) ** j for j in range(added - 1, -1, -1)]]
        past = increments[:index - 1]
        mean = np.sum(weights * past)
        variance = np.sum(weights * (past - mean) ** 2)
        sigma = np.sqrt(max(variance, SIGMA_FLOOR ** 2))
        np.testing.assert_allclose(output[index], [sequence[index, 0], increments[index - 1],
                                                  np.log(sigma), (increments[index - 1] - mean) / sigma], atol=1e-12)


def test_current_shock_and_future_values_cannot_change_its_forecast():
    baseline = np.zeros((24, 2))
    shocked = baseline.copy()
    shocked[8:] = 10
    a, b = ewma_features(baseline), ewma_features(shocked)
    np.testing.assert_allclose(a[8, 4:6], b[8, 4:6])  # Same prior volatility despite current shock.
    np.testing.assert_allclose(b[8, 6:], 10 / SIGMA_FLOOR)
    changed_future = shocked.copy()
    changed_future[13:] = -100
    np.testing.assert_allclose(ewma_features(changed_future)[:13], b[:13], equal_nan=True)
    # Adding a constant log power changes levels but leaves returns and volatility intact.
    shifted = ewma_features(shocked + 12)
    np.testing.assert_allclose(shifted[:, 2:], b[:, 2:], equal_nan=True)


def test_rejected_center_resets_history_without_bridging():
    rng = np.random.default_rng(8)
    sequence = rng.normal(size=(40, 3)).cumsum(axis=0)
    sequence[16] = np.nan
    result = ewma_features(sequence)
    assert np.isnan(result[16:25]).all()
    assert np.isfinite(result[25]).all()
    np.testing.assert_allclose(result[17:], ewma_features(sequence[17:]), equal_nan=True)
    sequence[16] = np.inf
    with pytest.raises(ValueError, match="two-dimensional"):
        ewma_features(sequence)


def test_identical_power_features_and_common_availability_masks():
    block = example_block()
    frame = temporal_frame(block.recording, block.eog)
    epochs, old_times, accepted = extract_workload_windows(prepare(block.recording, workload_config()))
    old_features = workload_features(epochs, "power")
    chosen = frame.evaluation_grid & frame.raw_valid
    np.testing.assert_array_equal(frame.times[chosen], old_times[accepted])
    np.testing.assert_allclose(frame.features["power"][chosen], old_features)
    for kind in frame.features:
        assert np.isfinite(frame.features[kind][frame.ready]).all()
    assert not frame.ready[frame.times == 3]
    assert frame.ready[frame.times == 5]
    quality = quality_counts(block, frame, "task_rest")
    assert quality["by_label"]["0"]["history_ready"] < quality["by_label"]["0"]["raw_valid"]


def test_grouped_training_frozen_scans_and_eye_export_rejection(tmp_path):
    blocks = [example_block(i, c) for i, c in enumerate((0, 2, 3, 3, 0, 2))]
    models = fit_temporal_models(blocks)
    assert len(models) == 10
    assert len({m.model_card["training_windows"] for (target, _), m in models.items() if target == "task_rest"}) == 1
    assert models[("task_rest", "power_ewma")].model_card["folds"] == [
        {"train_blocks": [3, 4, 5], "validation_blocks": [0, 1, 2]},
        {"train_blocks": [0, 1, 2], "validation_blocks": [3, 4, 5]}]
    with pytest.raises(ValueError, match="Only calibration"):
        fit_temporal_models([replace(b, role="evaluation") for b in blocks])
    heldout = example_block(7, 2, "evaluation")
    model = models[("task_rest", "power_ewma")]
    assert_heldout(heldout, model)
    before = joblib.hash(model)
    scan = model.scan(heldout.recording)
    assert joblib.hash(model) == before
    frame = temporal_frame(heldout.recording)
    np.testing.assert_allclose(scan["scores"], model.scan_frame(heldout.recording, frame)["scores"], equal_nan=True)
    with pytest.raises(ValueError, match="same calibrated"):
        model.scan(replace(heldout.recording, session_id="other"))
    with pytest.raises(ValueError, match="ocular preprocessing"):
        model.scan(replace(heldout.recording, processing_id="raw"))
    eye = models[("task_rest", "eog_power_ewma")]
    with pytest.raises(ValueError, match="Eye-only"):
        eye.scan(heldout.recording)
    with pytest.raises(ValueError, match="Only EEG"):
        export_temporal_events(heldout.recording, eye, scan)
    events = export_temporal_events(heldout.recording, model, scan, 20)
    assert all(e["source"] == "replayed_eeg" and e["confidence"] is None for e in events)
    assert all(e["anchor_s"] == e["eeg_anchor_s"] + 20 for e in events)
    joblib.dump(model, tmp_path / "model.joblib")
    restored = joblib.load(tmp_path / "model.joblib")
    np.testing.assert_allclose(scan["scores"], restored.scan(heldout.recording)["scores"], equal_nan=True)
