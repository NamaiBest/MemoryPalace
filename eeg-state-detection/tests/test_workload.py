from dataclasses import replace

import joblib
import numpy as np
import pytest

from eeg_moments.data import Recording
from eeg_moments.shin import EEG_CHANNELS, RealBlock
from eeg_moments.signal import Prepared
from eeg_moments.workload import (SustainedTangentFeatures, WorkloadModel, export_workload_events,
                                  extract_workload_windows, fit_workload, labels_for_times,
                                  segment_scores, workload_metrics)
from eeg_moments.workload_benchmark import assert_heldout, interval_assessment


def example_block(index=0, condition=0, role="calibration"):
    rng = np.random.default_rng(91 + index)
    t = np.arange(12800) / 200
    amplitude = np.where((t >= 10) & (t < 54), 2 + condition, 0.5)
    data = rng.normal(0, 0.4, (28, len(t))) + amplitude * np.sin(2 * np.pi * 6 * t)
    rec = Recording(data, 200, EEG_CHANNELS, "session", f"block{index}", "replayed_eeg",
                    processing_id="test-ocular-fit")
    return RealBlock(rec, index, condition, role, index * 70, 10, 54, [],
                     [[2, 6], [58, 62]], rng.normal(0, 0.2, (2, len(t))))


def test_window_labels_never_straddle_transitions():
    block = example_block()
    times = np.array([2.75, 3, 5, 5.25, 12.75, 13, 51, 51.25, 59, 61, 61.25])
    np.testing.assert_array_equal(labels_for_times(block, times, "task_rest"),
                                  [-1, 0, 0, -1, -1, 1, 1, -1, 0, 0, -1])
    np.testing.assert_array_equal(labels_for_times(block, times, "high_low"),
                                  [-1, -1, -1, -1, -1, 0, 0, -1, -1, -1, -1])


def test_invalid_windows_preserve_grid_and_break_stretches():
    block = example_block()
    prepared = Prepared(block.recording, block.recording.samples[None], np.zeros(12800, dtype=bool))
    prepared.bad[600] = True
    epochs, times, accepted = extract_workload_windows(prepared)
    assert epochs.shape[1:] == (1, 28, 400)
    assert 3 not in times[accepted]
    np.testing.assert_allclose(np.diff(times), 2)
    dense = np.arange(0, 10.25, 0.25)
    scores = np.ones(len(dense))
    scores[dense == 2] = np.nan  # No interval may span this invalid point.
    scores[dense >= 8] = -1
    intervals = segment_scores(dense, scores)
    assert len(intervals) == 1
    assert intervals[0]["start_s"] == 2.25
    assert intervals[0]["confirmed_s"] == 5.25
    assert intervals[0]["end_s"] == 8
    with pytest.raises(ValueError, match="full 0.25"):
        segment_scores(np.delete(dense, 8), np.delete(scores, 8))


def test_tangent_transform_is_batch_independent_and_frozen():
    rng = np.random.default_rng(19)
    X = rng.normal(size=(20, 3, 4, 4))
    X = X @ np.swapaxes(X, -1, -2) + 2 * np.eye(4)
    mapping = SustainedTangentFeatures().fit(X[:12])
    before = joblib.hash(mapping)
    first = mapping.transform(X[12:13])
    batch = mapping.transform(X[12:])
    np.testing.assert_allclose(first[0], batch[0], atol=1e-12)
    assert joblib.hash(mapping) == before


def test_training_groups_validation_and_export_contract(tmp_path):
    blocks = [example_block(i, c) for i, c in enumerate((0, 2, 3, 3, 0, 2))]
    model = fit_workload(blocks)
    assert model.model_card["folds"] == [
        {"train_blocks": [3, 4, 5], "validation_blocks": [0, 1, 2]},
        {"train_blocks": [0, 1, 2], "validation_blocks": [3, 4, 5]}]
    with pytest.raises(ValueError, match="Only calibration"):
        fit_workload([replace(b, role="evaluation") for b in blocks])
    with pytest.raises(ValueError, match="Do not pool"):
        fit_workload(blocks[:-1] + [replace(blocks[-1], recording=replace(blocks[-1].recording, session_id="other"))])
    with pytest.raises(ValueError, match="same calibrated"):
        model.scan(replace(blocks[0].recording, session_id="other"))
    with pytest.raises(ValueError, match="ocular preprocessing"):
        model.scan(replace(blocks[0].recording, processing_id="raw"))
    with pytest.raises(ValueError, match="calibration block"):
        assert_heldout(blocks[0], model)
    with pytest.raises(ValueError, match="duplicate"):
        assert_heldout(replace(blocks[0], role="evaluation", recording=replace(blocks[0].recording, recording_id="hidden-copy")), model)
    unseen = example_block(8, 2, "evaluation")
    assert_heldout(unseen, model)
    before = joblib.hash(model)
    scan = model.scan(unseen.recording)
    assert joblib.hash(model) == before
    joblib.dump(model, tmp_path / "model.joblib")
    restored = joblib.load(tmp_path / "model.joblib")
    restored_scan = restored.scan(unseen.recording)
    np.testing.assert_allclose(restored_scan["scores"], scan["scores"], equal_nan=True)
    assert restored_scan["stretches"] == scan["stretches"]
    events = export_workload_events(unseen.recording, model, scan, 100)
    assert events  # Controlled synthetic separation exercises the path, not biology.
    assert all(e["source"] == "replayed_eeg" and e["confidence"] is None for e in events)
    assert all(e["anchor_s"] == e["eeg_anchor_s"] + 100 for e in events)
    assert all(e["signal_type"] == "stretch" and e["duration_s"] >= 3 for e in events)
    assert events == sorted(events, key=lambda e: e["anchor_s"])
    assert len({e["event_id"] for e in events}) == len(events)


def test_eye_control_cannot_export_or_score_eeg_windows():
    block = example_block()
    model = WorkloadModel("session", "eog_power", "task_rest", None, {"processing_id": "test-ocular-fit"})
    with pytest.raises(ValueError, match="eye-only"):
        model.scan(block.recording)
    with pytest.raises(ValueError, match="Only EEG"):
        export_workload_events(block.recording, model, {"stretches": []})


def test_interval_fragmentation_is_not_a_full_task_match():
    block = example_block()
    intervals = [{"start_s": 10, "end_s": 20}, {"start_s": 22, "end_s": 32},
                 {"start_s": 34, "end_s": 44}, {"start_s": 46, "end_s": 54}]
    result = interval_assessment(block, intervals)
    assert result["true_positives"] == 0
    assert result["task_covered_s"] == 38
    assert result["rest_covered_s"] == 0
    metrics = workload_metrics([0, 0, 1, 1], [-1, -2, 2, 1])
    assert metrics["auroc"] == metrics["balanced_accuracy"] == 1
    assert workload_metrics([], [])["auroc"] is None
