import numpy as np
import pytest

from eeg_moments.backtest import dig, null_distribution, shifted, summarize_null


def test_shift_keeps_values_and_validity_and_moves_them():
    rng = np.random.default_rng(0)
    scores = np.array([np.nan, 1.0, 2.0, np.nan, 3.0, 4.0, 5.0])
    valid = np.isfinite(scores)
    moved = shifted(scores, valid, rng)
    np.testing.assert_array_equal(np.isfinite(moved), valid)
    assert sorted(moved[valid]) == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert not np.array_equal(moved[valid], scores[valid])
    single = np.array([np.nan, 7.0])
    np.testing.assert_array_equal(shifted(single, np.isfinite(single), rng), single)


def test_null_is_calibrated_on_an_uninformative_trace_and_flags_a_real_one():
    rng = np.random.default_rng(1)
    times = np.arange(0, 64, 0.25)
    labels = np.full(len(times), -1)
    labels[(times >= 12) & (times <= 52)] = 1
    labels[(times >= 2) & (times <= 6)] = 0
    labels[(times >= 58) & (times <= 62)] = 0
    use = (np.arange(len(times)) % 8 == 0) & (labels >= 0)
    noise = rng.normal(size=len(times))
    block = {"times": times, "scores": noise, "valid": np.ones(len(times), bool), "labels": labels, "use": use}
    auroc, _ = null_distribution([block], rng, 300)
    assert 0.35 < np.nanmean(auroc) < 0.65
    aligned = np.where(labels == 1, 3.0, -3.0) + 0.1 * noise
    real = dict(block, scores=aligned)
    from eeg_moments.workload import workload_metrics
    observed = workload_metrics(labels[use], aligned[use])["auroc"]
    auroc, _ = null_distribution([real], rng, 300)
    summary = summarize_null(auroc, observed)
    assert observed == 1.0 and summary["probability_at_least_observed"] < 0.1
    assert summarize_null(np.full(5, np.nan), 0.9) is None
    assert dig({"a": {"b": [1, 2]}}, ("a", "b", 1)) == 2
