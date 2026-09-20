from dataclasses import replace

import joblib
import numpy as np
import pytest
from scipy.signal import get_window, periodogram

from eeg_moments.fourier import (FINE_BANDS, export_fourier_events, fit_fourier_models,
                                 fourier_psd, spectral_features, spectral_frame)
from eeg_moments.signal import prepare
from eeg_moments.workload import extract_workload_windows, workload_config, workload_features
from eeg_moments.workload_benchmark import assert_heldout
from test_workload import example_block


def test_fft_density_agrees_with_scipy_and_parseval():
    rng = np.random.default_rng(42)
    signal = rng.normal(size=(5, 3, 400)) + 200
    frequencies, density = fourier_psd(signal)
    expected_f, expected = periodogram(signal, fs=200, window="hann", detrend="constant", scaling="density", axis=-1)
    np.testing.assert_array_equal(frequencies, expected_f)
    np.testing.assert_allclose(density, expected, atol=1e-13)
    taper = get_window("hann", 400, fftbins=True)
    time_power = ((signal - signal.mean(axis=-1, keepdims=True)) ** 2 * taper ** 2).sum(axis=-1) / (taper ** 2).sum()
    np.testing.assert_allclose(density.sum(axis=-1) * 0.5, time_power, atol=1e-12)


def test_dc_nyquist_and_amplitude_scaling():
    t = np.arange(400) / 200
    data = np.stack([np.full(400, 30.0), (-1.0) ** np.arange(400), 3 * np.sin(2 * np.pi * 10.25 * t)])[None]
    frequencies, density = fourier_psd(data)
    assert not density[0, 0].any()
    assert density[0, 1].sum() * 0.5 == pytest.approx(1.0)  # Nyquist must not be doubled.
    assert frequencies[np.argmax(density[0, 2])] in (10.0, 10.5)
    _, scaled = fourier_psd(2 * data)
    np.testing.assert_allclose(scaled, 4 * density, atol=1e-12)
    with pytest.raises(ValueError, match="two seconds"):
        fourier_psd(data[..., :200])


def test_frequency_bins_partition_the_same_band_power():
    rng = np.random.default_rng(8)
    frequencies, density = fourier_psd(rng.normal(size=(4, 28, 400)))
    fine = np.exp(spectral_features(frequencies, density, FINE_BANDS)).reshape(4, 26, 28)
    bands = np.exp(spectral_features(frequencies, density, workload_config().bands)).reshape(4, 3, 28)
    np.testing.assert_allclose(fine[:, :4].sum(axis=1), bands[:, 0], atol=1e-12)
    np.testing.assert_allclose(fine[:, 4:9].sum(axis=1), bands[:, 1], atol=1e-12)
    np.testing.assert_allclose(fine[:, 9:].sum(axis=1), bands[:, 2], atol=1e-12)


def test_reference_features_quality_and_window_clock_are_unchanged():
    block = example_block()
    frame = spectral_frame(block.recording, block.eog)
    epochs, times, accepted = extract_workload_windows(prepare(block.recording, workload_config()))
    use = frame.evaluation_grid & frame.valid
    np.testing.assert_array_equal(frame.times[use], times[accepted])
    np.testing.assert_allclose(frame.features["power"][use], workload_features(epochs, "power"))
    assert frame.valid[frame.times == 3]  # No volatility warm-up added to the Fourier experiment.
    assert frame.features["fft_bins"].shape[1] == 728
    assert frame.features["eog_fft_bins"].shape[1] == 52
    for values in frame.features.values():
        np.testing.assert_array_equal(np.isfinite(values).all(axis=1), frame.valid)
    broken = replace(block.recording, samples=block.recording.samples.copy())
    broken.samples[0, 30 * 200] += 1000
    artifact = spectral_frame(broken)
    assert not artifact.valid[artifact.times == 30]


def test_fold_isolation_frozen_scans_and_provenance(tmp_path):
    blocks = [example_block(i, c) for i, c in enumerate((0, 2, 3, 3, 0, 2))]
    models = fit_fourier_models(blocks)
    assert len(models) == 12
    cards = [m.model_card for (target, _), m in models.items() if target == "task_rest"]
    assert all(c["quality"] == cards[0]["quality"] and c["folds"] == cards[0]["folds"] for c in cards)
    assert cards[0]["folds"] == [
        {"train_blocks": [3, 4, 5], "validation_blocks": [0, 1, 2]},
        {"train_blocks": [0, 1, 2], "validation_blocks": [3, 4, 5]}]
    with pytest.raises(ValueError, match="Only calibration"):
        fit_fourier_models([replace(b, role="evaluation") for b in blocks])
    block = example_block(7, 2, "evaluation")
    model = models[("task_rest", "fft_bins")]
    assert_heldout(block, model)
    before = joblib.hash(model)
    scan = model.scan(block.recording)
    assert joblib.hash(model) == before
    frame = spectral_frame(block.recording)
    np.testing.assert_allclose(scan["scores"], model.scan_frame(block.recording, frame)["scores"], equal_nan=True)
    with pytest.raises(ValueError, match="same calibrated"):
        model.scan(replace(block.recording, session_id="other"))
    with pytest.raises(ValueError, match="ocular preprocessing"):
        model.scan(replace(block.recording, processing_id="raw"))
    with pytest.raises(ValueError, match="Eye-only"):
        models[("task_rest", "eog_fft_bins")].scan(block.recording)
    with pytest.raises(ValueError, match="Only EEG"):
        export_fourier_events(block.recording, models[("task_rest", "eog_fft_bins")], scan)
    events = export_fourier_events(block.recording, model, scan, 20)
    assert all(e["source"] == "replayed_eeg" and e["confidence"] is None for e in events)
    assert all(e["anchor_s"] == e["eeg_anchor_s"] + 20 for e in events)
    joblib.dump(model, tmp_path / "model.joblib")
    restored = joblib.load(tmp_path / "model.joblib")
    np.testing.assert_allclose(restored.scan(block.recording)["scores"], scan["scores"], equal_nan=True)
