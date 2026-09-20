from types import SimpleNamespace

import numpy as np
import pytest

from eeg_moments.benchmark import retrieval_metrics
from eeg_moments.burst_diagnostic import BUDGET, SEPARATION_S, TOLERANCE_S, block_frame, draw_flags, null_totals


def example_block():
    # Stimuli every 2.2 s from 10 s; targets at trials 2, 5 and 8 (0-based).
    trials = [{"time_s": 10 + 2.2 * i, "label": int(i in (2, 5, 8))} for i in range(10)]
    task_end = trials[-1]["time_s"] + 2.2
    rec = SimpleNamespace(session_id="s", recording_id="r", duration_s=task_end + 10)
    return SimpleNamespace(recording=rec, trials=trials, task_start_s=10.0, task_end_s=task_end, condition=2)


def test_grid_categories_follow_marker_distances():
    block = example_block()
    times = np.round(np.arange(0.1, block.recording.duration_s - 1.0, 0.1), 6)
    frame = block_frame(block, times)
    target = 10 + 2.2 * 2
    assert frame["category"][np.argmin(np.abs(times - target))] == "target_window"
    assert frame["category"][np.argmin(np.abs(times - (target + TOLERANCE_S + 0.1)))] == "between_stimuli"
    assert frame["category"][np.argmin(np.abs(times - (10 + 2.2 * 3)))] == "nontarget_window"
    assert frame["category"][np.argmin(np.abs(times - 3.0))] == "context_margin"
    assert frame["category"][np.argmin(np.abs(times - (block.task_end_s + 5)))] == "context_margin"
    # Target windows take precedence over adjacent non-target windows; every onset is grid-aligned.
    assert (frame["onset_aligned"] == 1).sum() == 3 and (frame["onset_aligned"] == 0).sum() == 7
    assert frame["signed_offset"][np.argmin(np.abs(times - (target + 0.3)))] == pytest.approx(0.3, abs=1e-6)
    with pytest.raises(ValueError, match="both"):
        block_frame(SimpleNamespace(**{**vars(block), "trials": [{"time_s": 12.0, "label": 1}]}), times)


def test_random_flags_respect_budget_separation_and_pool():
    block = example_block()
    times = np.round(np.arange(0.1, block.recording.duration_s - 1.0, 0.1), 6)
    frame = block_frame(block, times)
    rng = np.random.default_rng(0)
    for _ in range(50):
        flags = draw_flags(times, rng, np.arange(len(times)))
        anchors = sorted(f["anchor_s"] for f in flags)
        assert len(flags) == BUDGET
        assert all(b - a >= SEPARATION_S - 1e-9 for a, b in zip(anchors, anchors[1:]))
    onsets = {round(t["time_s"], 6) for t in block.trials}
    for _ in range(50):
        flags = draw_flags(times, rng, np.flatnonzero(frame["onset_aligned"] >= 0))
        assert all(round(f["anchor_s"], 6) in onsets for f in flags)
    # A stimulus-blind draw of five out of ten onsets with three targets matches 1.5 on average.
    totals = null_totals([(block, times, np.zeros(len(times)), frame)], np.random.default_rng(1), "stimulus_blind", draws=4000)
    assert totals.mean() == pytest.approx(1.5, abs=0.06)
    uniform = null_totals([(block, times, np.zeros(len(times)), frame)], np.random.default_rng(2), "uniform", draws=2000)
    assert 0 < uniform.mean() < 1.5
    truth = {"bursts": [{"anchor_s": 10 + 2.2 * 2}]}
    assert retrieval_metrics([{"anchor_s": 10 + 2.2 * 2 + TOLERANCE_S, "raw_score": 1.0}], truth, TOLERANCE_S)["true_positives"] == 1
