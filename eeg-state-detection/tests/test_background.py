from pathlib import Path

import numpy as np
import pytest

from eeg_moments.background_benchmark import assert_fresh, run_background_benchmark
from eeg_moments.data import Recording
from eeg_moments.erp import background_centres, fit_erp
from eeg_moments.shin import EEG_CHANNELS, RealBlock


def trial_block(index, condition, role="calibration"):
    """Twenty stimuli 2.2 s apart from 10.12 s; six targets carry a short frontal-central deflection."""
    rng = np.random.default_rng(300 + index)
    t = np.arange(12900) / 200
    data = rng.normal(0, 1.0, (28, len(t)))
    trials = []
    for k in range(20):
        onset = 10.12 + 2.2 * k
        label = int(k in (2, 5, 8, 11, 14, 17))
        trials.append({"time_s": onset, "label": label, "code": 48 if label else 64})
        window = (t >= onset + 0.3) & (t < onset + 0.6)
        data[:, window] += 6.0 * label
    rec = Recording(data, 200, EEG_CHANNELS, "session", f"block{index}", "replayed_eeg", processing_id="test-ocular-fit")
    task_end = trials[-1]["time_s"] + 2.2
    return RealBlock(rec, index, condition, role, index * 70, 10.0, task_end, trials,
                     [[2, 6], [task_end + 4, task_end + 8]], rng.normal(0, 0.2, (2, len(t))))


def test_background_centres_avoid_every_stimulus():
    trials = [{"time_s": 10.13 + 2.2 * k, "label": 0} for k in range(5)]
    centres = background_centres(trials, 30.0)
    assert np.allclose(np.diff(centres)[np.diff(centres) < 0.6], 0.5)
    for centre in centres:
        assert min(abs(centre - t["time_s"]) for t in trials) > 0.5
    assert 0.1 <= centres.min() and centres.max() < 29.0
    assert len(background_centres([], 5.0)) == len(np.arange(0.1, 4.0, 0.5))


def test_background_arm_adds_calibration_only_negatives_and_scans():
    blocks = [trial_block(i, c) for i, c in enumerate((2, 3, 2, 3))]
    baseline = fit_erp(blocks, "mean_bins")
    background = fit_erp(blocks, "mean_bins_background")
    assert background.kind == "mean_bins_background"
    extra = background.model_card["background_negatives"]
    assert extra["step_s"] == 0.5 and extra["exclusion_s"] == 0.5 and extra["count"] > 100
    assert background.model_card["training_trials"] == baseline.model_card["training_trials"] + extra["count"]
    assert background.model_card["training_targets"] == baseline.model_card["training_targets"] == 24
    assert baseline.model_card["background_negatives"] is None
    for quality in background.model_card["quality"]:
        assert quality["background_epochs"] <= quality["background_candidates"]
    held_out = trial_block(8, 2, "evaluation")
    times, scores, rejected = background.scan(held_out.recording)
    assert len(times) == len(scores) and rejected >= 0
    assert_fresh(held_out, background)
    with pytest.raises(ValueError, match="held out"):
        assert_fresh(blocks[0], background)
    with pytest.raises(ValueError, match="Unknown ERP"):
        fit_erp(blocks, "background")


def test_runner_refuses_inspected_participants_and_nonempty_output(tmp_path):
    for name in ("VP001", "VP005"):
        with pytest.raises(ValueError, match="untouched"):
            run_background_benchmark(Path("data/shin2018") / name, tmp_path / "out")
    out = tmp_path / "busy"
    out.mkdir()
    (out / "report.json").write_text("{}")
    with pytest.raises(ValueError, match="not empty"):
        run_background_benchmark(Path("data/shin2018/VP006"), out)
