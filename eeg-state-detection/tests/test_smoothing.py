from dataclasses import replace

import joblib
import numpy as np
import pytest

from eeg_moments.smoothing import calibrate_smoothing, export_smoothed_events, smooth_scan
from eeg_moments.workload import fit_workload
from test_workload import example_block


def test_smoothing_half_life_and_gap_reset():
    scores = np.r_[0.0, np.ones(4), np.nan, -2.0, -2.0]
    raw = {"times": np.arange(len(scores)) * 0.25, "scores": scores,
           "valid": np.isfinite(scores), "stretches": []}
    result = smooth_scan(raw, 1.0)
    # Four updates at .25 s halve distance to the constant input.
    assert result["scores"][4] == pytest.approx(0.5, abs=1e-12)
    assert np.isnan(result["scores"][5])
    np.testing.assert_array_equal(result["scores"][6:], [-2, -2])
    np.testing.assert_array_equal(result["raw_scores"], scores)
    np.testing.assert_array_equal(result["valid"], raw["valid"])
    np.testing.assert_array_equal(raw["scores"], scores)
    for half in (-1, 0, np.nan, np.inf):
        with pytest.raises(ValueError, match="half-life"):
            smooth_scan(raw, half)
    with pytest.raises(ValueError, match="complete"):
        smooth_scan({**raw, "times": np.arange(len(scores)) * 0.5}, 1.0)


def test_smoothing_selection_preserves_original_weights_and_calibration_contract(tmp_path):
    blocks = [example_block(i, c) for i, c in enumerate((0, 2, 3, 3, 0, 2))]
    base = fit_workload(blocks)
    original = joblib.hash(base)
    model = calibrate_smoothing(blocks, base)
    assert model.base_model is base and joblib.hash(base) == original
    assert model.half_life_s in (0.5, 1.0, 2.0)
    assert model.model_card["selected_C"] == base.model_card["selected_C"]
    assert model.model_card["base_classifier_weights_unchanged"]
    assert len(model.model_card["smoothing_candidates"]) == 3
    assert all(len(r["fold_metrics"]) == 2 for r in model.model_card["smoothing_candidates"])
    rec = example_block(8, 2, "evaluation").recording
    scan = model.scan(rec)
    np.testing.assert_allclose(scan["raw_scores"], base.scan(rec)["scores"], equal_nan=True)
    assert joblib.hash(base) == original
    joblib.dump(model, tmp_path / "model.joblib")
    restored = joblib.load(tmp_path / "model.joblib")
    np.testing.assert_allclose(restored.scan(rec)["scores"], scan["scores"], equal_nan=True)
    for event in export_smoothed_events(rec, restored, scan, 100):
        assert event["confidence"] is None and event["source"] == "replayed_eeg"
        assert event["anchor_s"] == event["eeg_anchor_s"] + 100
        assert event["model_version"].startswith("smoothing-v1")
    with pytest.raises(ValueError, match="Only calibration"):
        calibrate_smoothing([replace(b, role="evaluation") for b in blocks], base)
    changed = replace(blocks[0], recording=replace(blocks[0].recording, samples=blocks[0].recording.samples + 1))
    with pytest.raises(ValueError, match="original training"):
        calibrate_smoothing([changed] + blocks[1:], base)
    with pytest.raises(ValueError, match="same calibrated"):
        model.scan(replace(rec, session_id="other"))
