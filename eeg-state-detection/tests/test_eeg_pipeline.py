from dataclasses import replace
import json

import joblib
import numpy as np
from pyriemann.utils.base import invsqrtm
from scipy.signal import butter, sosfiltfilt
import pytest

from eeg_moments.benchmark import evaluate, gate_metrics, random_active_gate, retrieval_metrics, stretch_metrics
from eeg_moments.data import Recording
from eeg_moments.model import BandTangentFeatures, covariances, export_events, select_events, train
from eeg_moments.signal import Config, StretchReference, gate_mask, make_windows, prepare
from eeg_moments.synthetic import simulate


@pytest.fixture(scope="module")
def config():
    return Config()


@pytest.fixture(scope="module")
def calibration():
    return [simulate(seed=i) for i in [51, 52, 53]]


@pytest.fixture(scope="module")
def fitted(calibration):
    return train(calibration, kind="tangent")


def test_recording_roundtrip_has_no_injection_truth(tmp_path):
    rec, truth = simulate()
    path = tmp_path / "recording.npz"
    rec.save(path)
    loaded = Recording.load(path)
    np.testing.assert_array_equal(rec.samples, loaded.samples)
    assert rec.session_id == loaded.session_id
    with np.load(path, allow_pickle=False) as obj:
        assert set(obj.files) == {"samples", "sample_rate", "channels", "units", "session_id", "recording_id", "source", "processing_id"}
    assert len(truth["bursts"]) == 3


@pytest.mark.parametrize("violation", ["missing", "reordered", "units", "rate", "nonfinite"])
def test_contract_fails_loudly(violation, config):
    rec, _ = simulate()
    if violation == "missing":
        rec = replace(rec, samples=rec.samples[:-1], channels=rec.channels[:-1])
    elif violation == "reordered":
        rec = replace(rec, channels=tuple(reversed(rec.channels)))
    elif violation == "units":
        rec = replace(rec, units="V")
    elif violation == "rate":
        rec = replace(rec, sample_rate=256)
    else:
        rec.samples[0, 500] = np.nan
    with pytest.raises(ValueError):
        prepare(rec, config)


def test_tangent_geometry_matches_independent_eigendecomposition():
    rng = np.random.default_rng(0)
    epochs = rng.normal(size=(12, 3, 2, 4, 100)) * np.arange(1, 5)[None, None, None, :, None]
    covs = covariances(epochs)
    assert np.linalg.eigvalsh(covs).min() > 0
    transform = BandTangentFeatures().fit(covs[:8])
    before = [mapping.reference_.copy() for mapping in transform.maps_]
    actual = transform.transform(covs[8:])
    expected = []
    upper = np.triu_indices(4)
    weights = np.where(upper[0] == upper[1], 1.0, np.sqrt(2))
    for b, reference in enumerate(before):
        invsqrt = invsqrtm(reference)
        vectors = []
        for context in range(3):
            matrices = []
            for cov in covs[8:, context, b]:
                values, directions = np.linalg.eigh(invsqrt @ cov @ invsqrt)
                matrix_log = (directions * np.log(values)) @ directions.T
                vector = matrix_log[upper] * weights
                np.testing.assert_allclose(np.linalg.norm(vector), np.linalg.norm(matrix_log), atol=1e-10)
                matrices.append(vector)
            vectors.append(np.asarray(matrices))
        expected.extend([vectors[0], vectors[0] - (vectors[1] + vectors[2]) / 2])
    np.testing.assert_allclose(actual, np.concatenate(expected, axis=1), atol=1e-10)
    # Transforming wildly different test covariances must not update the reference.
    transform.transform(covs[8:] * 100)
    for mapping, snapshot in zip(transform.maps_, before):
        np.testing.assert_array_equal(mapping.reference_, snapshot)


def test_artifact_rejection_and_filter_guard(config):
    rec, _ = simulate()
    processed = prepare(rec, config)
    windows = make_windows(processed, config)
    assert processed.bad[round(119 * rec.sample_rate)]
    assert not np.any(np.abs(windows.times - 119) < config.filter_guard_s)
    assert windows.rejected > 0
    # Inspect actual zero-phase filter support; the 2 s guard is numerical, not exact support.
    impulse = np.zeros(round(20 * config.sample_rate))
    middle = len(impulse) // 2
    impulse[middle] = 1
    far = np.abs(np.arange(len(impulse)) - middle) >= round(config.filter_guard_s * config.sample_rate)
    for band in config.bands:
        filtered = sosfiltfilt(butter(4, band, fs=config.sample_rate, btype="bandpass", output="sos"), impulse)
        assert np.max(np.abs(filtered[far])) < 1e-4


def test_stretch_confirmation_uses_onset_for_gate(calibration, config):
    processed = [prepare(rec, config) for rec, _ in calibration]
    reference = StretchReference.fit(processed, [truth["baseline_intervals_s"] for _, truth in calibration], config)
    stretches, _, _, _ = reference.detect(processed[0], config)
    assert len(stretches) >= 3
    event = stretches[0]
    assert event["confirmed_s"] - event["start_s"] >= config.stretch_min_s
    assert gate_mask(np.array([event["start_s"] - 2.5]), [event], config)[0]


def test_gate_coverage_union_and_random_match_count(config):
    times = np.arange(0, 70, 0.25)
    stretches = [{"start_s": 10, "end_s": 30}, {"start_s": 14, "end_s": 40}]
    mask = gate_mask(times, stretches, config)
    assert mask.sum() == np.count_nonzero((times >= 7) & (times <= 17))
    rng = np.random.default_rng(0)
    for _ in range(20):
        random = random_active_gate(times, stretches, mask, config, rng)
        assert random.sum() == mask.sum()
    truth = {"bursts": [{"anchor_s": 11}, {"anchor_s": 55}]}
    assert gate_metrics(times, mask, truth)["candidate_recall"] == 0.5


def test_ranking_abstention_and_one_to_one_matching(config):
    times = np.array([10, 10.25, 10.5, 40])
    scores = np.array([2, 5, 3, -2])
    mask = np.ones(4, dtype=bool)
    events = select_events(times, scores, mask, config)
    assert [e["anchor_s"] for e in events] == [10.25]
    assert select_events(times, -np.ones(4), mask, config) == []
    assert select_events(times, scores, mask, config, top_k=0) == []
    duplicate = [{"anchor_s": 10, "raw_score": 4}, {"anchor_s": 10.2, "raw_score": 2}]
    metrics = retrieval_metrics(duplicate, {"bursts": [{"anchor_s": 10.1}]})
    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1


def test_rejects_session_and_source_transfer(fitted):
    rec, _ = simulate(seed=80, session_seed=1234)
    with pytest.raises(ValueError, match="recalibration"):
        fitted.scan(rec)
    rec, _ = simulate(seed=80)
    with pytest.raises(ValueError, match="provenance"):
        fitted.scan(replace(rec, source="recorded_eeg"))


def test_duplicate_calibration_and_evaluation_guard(calibration, fitted):
    with pytest.raises(ValueError, match="distinct"):
        train([calibration[0], calibration[0], calibration[1]])
    rec, truth = calibration[0]
    with pytest.raises(ValueError, match="training"):
        evaluate(fitted, rec, truth)
    with pytest.raises(ValueError, match="duplicate"):
        evaluate(fitted, replace(rec, recording_id="renamed"), truth)


def test_saved_model_offline_inference_and_timestamp_offset(fitted, tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(fitted, path)
    loaded = joblib.load(path)
    rec, _ = simulate(seed=82)
    events, _ = loaded.detect(rec, scope="all")
    shifted, _ = loaded.detect(rec, scope="all", offset_s=12, output_session_id="phone-001")
    assert events  # Basic positive control for the complete trained model.
    assert len(events) == len(shifted)
    for first, second in zip(events, shifted):
        assert second["anchor_s"] == first["anchor_s"] + 12
        assert second["source"] == "synthetic_eeg"
        assert second["session_id"] == "phone-001"
        assert second["confidence"] is None
    assert json.loads(json.dumps(shifted, allow_nan=False)) == shifted
    again, _ = loaded.detect(rec, scope="all", offset_s=12, output_session_id="phone-001")
    assert shifted == again


def test_all_flat_recording_rejected(config):
    rec, _ = simulate()
    rec.samples[:] = 0
    with pytest.raises(ValueError, match="usable"):
        prepare(rec, config)


def test_stretches_export_without_bursts_and_top_k_does_not_hide_them(fitted):
    rec, _ = simulate(seed=81, scenario="negative")
    events, scan = fitted.detect(rec, top_k=0, scope="onset")
    assert len(events) == len(scan["stretches"]) >= 3
    assert all(e["signal_type"] == "stretch" for e in events)
    assert all(e["duration_s"] >= fitted.config.stretch_min_s for e in events)
    assert all(e["start_s"] <= e["confirmed_s"] < e["end_s"] for e in events)
    assert all(e["overlapping_burst_ids"] == [] for e in events)


def test_burst_stretch_overlap_keeps_distinct_events_and_offsets(fitted):
    rec, _ = simulate(seed=82)
    stretch = {"start_s": 20, "confirmed_s": 23, "end_s": 40, "peak_z": 6}
    selected = [{"anchor_s": 30, "raw_score": 3}, {"anchor_s": 60, "raw_score": 2}]
    events = export_events(rec, fitted, selected, offset_s=7, stretches=[stretch])
    assert [e["signal_type"] for e in events] == ["stretch", "burst", "burst"]
    first, inner, outer = events
    assert first["anchor_s"] == 27 and first["confirmed_s"] == 30 and first["end_s"] == 47
    assert first["overlapping_burst_ids"] == [inner["event_id"]]
    assert inner["overlapping_stretch_ids"] == [first["event_id"]]
    assert outer["overlapping_stretch_ids"] == []
    assert len({e["event_id"] for e in events}) == 3
    assert all(e["confidence"] is None for e in events)
    bursts_only = export_events(rec, fitted, selected)
    assert len(bursts_only) == 2 and all(e["signal_type"] == "burst" for e in bursts_only)


def test_stretch_interval_metrics_do_not_reward_duplicate_or_unrelated_intervals():
    truth = {"stretches": [{"start_s": 20, "end_s": 40}, {"start_s": 70, "end_s": 90}]}
    detected = [{"start_s": 19, "end_s": 41}, {"start_s": 20, "end_s": 40},
                {"start_s": 120, "end_s": 140}]
    metrics = stretch_metrics(detected, truth)
    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 2
    assert metrics["false_negatives"] == 1
    assert metrics["mean_iou"] == 1


def test_baseline_control_has_no_injected_signal_and_can_abstain(fitted):
    rec, truth = simulate(seed=83, scenario="baseline")
    assert truth["bursts"] == truth["stretches"] == []
    events, _ = fitted.detect(rec)
    assert events == []
