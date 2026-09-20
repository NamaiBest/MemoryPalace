from dataclasses import replace
from unittest.mock import Mock

import numpy as np
import pytest

import joblib

from eeg_moments.combined import detect_combined
from eeg_moments.data import Recording
from eeg_moments.erp import ERPModel
from eeg_moments.shin import EEG_CHANNELS
from eeg_moments.smoothing import SmoothedPowerModel, export_smoothed_events
from eeg_moments.workload import WorkloadModel, export_workload_events

LINK_FIELDS = ("overlapping_stretch_ids", "nearest_stretch_onset_s", "offset_from_stretch_onset_s", "within_onset_gate")


@pytest.fixture
def branches():
    rec = Recording(np.zeros((28, 6000)), 200, EEG_CHANNELS, "session", "excerpt", "replayed_eeg",
                    processing_id="frozen-ocular")
    card = {"processing_id": rec.processing_id}
    workload = WorkloadModel("session", "power", "task_rest", None, card.copy())
    erp = ERPModel("session", "mean_bins", None, card.copy())
    grid = np.arange(1, 29.25, 0.25)
    workload.scan = Mock(return_value={
        "times": grid, "valid": np.ones(len(grid), dtype=bool),
        "stretches": [{"start_s": 4.0, "confirmed_s": 7.0, "end_s": 12.0, "peak_score": 9.0}]})
    erp.scan = Mock(return_value=(np.array([0.1, 5.0, 15.0, 20.0, 28.9]),
                                 np.array([1.0, 4.0, 3.0, -1.0, 2.0]), 2))
    return rec, workload, erp


def test_union_retains_ungated_bursts_and_existing_stretches(branches):
    rec, workload, erp = branches
    events, diagnostics = detect_combined(rec, workload, erp, offset_s=100)
    assert diagnostics["event_counts"] == {"stretch": 1, "burst": 4}
    assert diagnostics["bursts_overlapping_stretches"] == 1
    assert events == sorted(events, key=lambda e: (e["anchor_s"], e["event_id"]))
    stretch = next(e for e in events if e["signal_type"] == "stretch")
    standalone = export_workload_events(rec, workload, workload.scan.return_value, 100)[0]
    assert {**stretch, "overlapping_burst_ids": []} == standalone
    for event in events:
        assert event["anchor_s"] == event["eeg_anchor_s"] + 100
        assert 100 <= event["start_s"] <= event["anchor_s"] <= event["end_s"] <= 130
        assert event["confidence"] is None
        if event["signal_type"] == "burst":
            assert (stretch["event_id"] in event["overlapping_stretch_ids"]) == (event["eeg_anchor_s"] == 5)
            assert (event["event_id"] in stretch["overlapping_burst_ids"]) == (event["eeg_anchor_s"] == 5)
            assert event["start_s"] == pytest.approx(event["anchor_s"] - 0.1)
            assert event["end_s"] == pytest.approx(event["anchor_s"] + 1.0)
    before = [(e["eeg_anchor_s"], e["raw_score"], e["rank"]) for e in events if e["signal_type"] == "burst"]
    workload.scan.return_value["stretches"] = []
    burst_only, _ = detect_combined(rec, workload, erp)
    assert [(e["eeg_anchor_s"], e["raw_score"], e["rank"]) for e in burst_only] == before
    assert all(not e["overlapping_stretch_ids"] and e["nearest_stretch_onset_s"] is None for e in burst_only)


@pytest.mark.parametrize("top_k,burst_count", [(0, 0), (1, 1), (2, 2)])
def test_burst_budget_never_limits_stretches(branches, top_k, burst_count):
    rec, workload, erp = branches
    events, diagnostic = detect_combined(rec, workload, erp, top_k=top_k)
    assert diagnostic["event_counts"] == {"stretch": 1, "burst": burst_count}
    assert sum(e["signal_type"] == "stretch" for e in events) == 1


def test_missing_burst_candidates_keep_stretches(branches):
    rec, workload, erp = branches
    erp.scan.return_value = (np.empty(0), np.empty(0), 20)
    events, diagnostic = detect_combined(rec, workload, erp)
    assert len(events) == 1 and events[0]["signal_type"] == "stretch"
    assert diagnostic["burst_rejected_windows"] == diagnostic["burst_windows"] == 20


@pytest.mark.parametrize("field,value", [("session_id", "other"), ("processing_id", "raw"),
                                        ("source", "synthetic_eeg"), ("sample_rate", 128)])
def test_mismatched_input_rejected_before_either_scan(branches, field, value):
    rec, workload, erp = branches
    with pytest.raises(ValueError):
        detect_combined(replace(rec, **{field: value}), workload, erp)
    workload.scan.assert_not_called()
    erp.scan.assert_not_called()


def test_second_model_mismatch_rejected_before_first_scan(branches):
    rec, workload, erp = branches
    erp.session_id = "different-calibration"
    with pytest.raises(ValueError, match="same calibrated"):
        detect_combined(rec, workload, erp)
    workload.scan.assert_not_called()


@pytest.mark.parametrize("which", ["workload", "erp"])
def test_eye_controls_cannot_enter_union(branches, which):
    rec, workload, erp = branches
    if which == "workload":
        workload.kind = "eog_power"
    else:
        erp.kind = "eog_bins"
    with pytest.raises(ValueError, match="Eye-only"):
        detect_combined(rec, workload, erp)
    workload.scan.assert_not_called()
    erp.scan.assert_not_called()


@pytest.fixture
def smoothed(branches):
    """Wrap the same base model; raw margins step to +1 between 4 and 12 s and are -1 elsewhere."""
    rec, workload, erp = branches
    grid = workload.scan.return_value["times"]
    scores = np.where((grid >= 4.0) & (grid < 12.0), 1.0, -1.0)
    workload.scan = Mock(return_value={"times": grid, "scores": scores, "valid": np.isfinite(scores), "stretches": []})
    card = {**workload.model_card, "kind": "power_ema", "half_life_s": 2.0, "base_classifier_weights_unchanged": True}
    return rec, SmoothedPowerModel(workload, 2.0, card), erp


def test_smoothed_stretch_branch_exports_smoothed_scores_and_leaves_bursts_unchanged(branches, smoothed):
    rec, workload, erp = branches
    unsmoothed_events, unsmoothed_diagnostics = detect_combined(rec, workload, erp, offset_s=100)
    rec, model, erp = smoothed
    events, diagnostics = detect_combined(rec, model, erp, offset_s=100)
    assert diagnostics["stretch_model_kind"] == "power_ema" and diagnostics["stretch_half_life_s"] == 2.0
    assert unsmoothed_diagnostics["stretch_model_kind"] == "power" and unsmoothed_diagnostics["stretch_half_life_s"] is None
    stretches = [e for e in events if e["signal_type"] == "stretch"]
    assert len(stretches) == 1
    stretch = stretches[0]
    # Same event as the standalone smoothed export, apart from navigation links.
    standalone = export_smoothed_events(rec, model, model.scan(rec), 100)
    assert [{**s, "overlapping_burst_ids": []} for s in stretches] == standalone
    assert stretch["model_version"] == "smoothing-v1-power-2s"
    assert stretch["score_definition"] == "peak exponentially smoothed linear decision margin"
    # The exported score is the smoothed peak, not the raw +1 margin, and onset lags the raw step.
    assert 0 < stretch["raw_score"] < 1
    assert stretch["eeg_anchor_s"] > 4.0 and stretch["anchor_s"] == stretch["eeg_anchor_s"] + 100
    assert stretch["overlapping_burst_ids"] == [e["event_id"] for e in events
                                                if e["signal_type"] == "burst" and stretch["event_id"] in e["overlapping_stretch_ids"]]
    # Bursts are identical whichever stretch model is loaded; only their stretch links may differ.
    strip = lambda e: {k: v for k, v in e.items() if k not in LINK_FIELDS}
    assert ([strip(e) for e in events if e["signal_type"] == "burst"]
            == [strip(e) for e in unsmoothed_events if e["signal_type"] == "burst"])
    assert diagnostics["event_counts"]["burst"] == unsmoothed_diagnostics["event_counts"]["burst"] == 4


def test_smoothed_eye_control_cannot_enter_union(smoothed):
    rec, model, erp = smoothed
    model.base_model.kind = "eog_power"
    with pytest.raises(ValueError, match="Eye-only"):
        detect_combined(rec, model, erp)
    model.base_model.scan.assert_not_called()
    erp.scan.assert_not_called()


def test_replay_loader_refuses_branch_file_mismatch(tmp_path):
    from eeg_moments.combined_replay import load_stretch_model
    card = {"processing_id": "frozen-ocular"}
    power = WorkloadModel("session", "power", "task_rest", None, card)
    ema = SmoothedPowerModel(power, 0.5, {**card, "kind": "power_ema", "half_life_s": 0.5,
                                          "base_classifier_weights_unchanged": True})
    joblib.dump(power, tmp_path / "power.joblib")
    joblib.dump(ema, tmp_path / "ema.joblib")
    assert load_stretch_model(tmp_path / "power.joblib", "power").kind == "power"
    assert load_stretch_model(tmp_path / "ema.joblib", "power_ema").half_life_s == 0.5
    for name, kind in (("power.joblib", "power_ema"), ("ema.joblib", "power")):
        with pytest.raises(ValueError, match="Expected"):
            load_stretch_model(tmp_path / name, kind)
    uncertified = SmoothedPowerModel(power, 0.5, {**card, "kind": "power_ema"})
    joblib.dump(uncertified, tmp_path / "uncertified.joblib")
    with pytest.raises(ValueError, match="certify"):
        load_stretch_model(tmp_path / "uncertified.joblib", "power_ema")
    with pytest.raises(ValueError, match="Unknown"):
        load_stretch_model(tmp_path / "power.joblib", "tangent")
