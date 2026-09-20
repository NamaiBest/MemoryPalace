from dataclasses import replace

import numpy as np
import pytest

from eeg_moments.erp import ERPMeanBins, ERPModel, classification_metrics, extract_epochs, fit_erp
from eeg_moments.shin import EEG_CHANNELS, RealBlock, audit_blocks, parse_markers
from eeg_moments.signal import Config, prepare
from eeg_moments.synthetic import simulate


def markers():
    events = []
    for i, condition in enumerate((3, 2, 0, 2, 0, 3, 0, 3, 2)):
        start = 20 + 70 * i
        blockcode = {0: 112, 2: 128, 3: 144}[condition]
        events.append({"code": blockcode, "time_s": start, "sample": start * 1000})
        for trial in range(20):
            code = 16 if condition == 0 else ({2: 48, 3: 80}[condition] if trial < 6 else {2: 64, 3: 96}[condition])
            time = start + 0.12 + trial * 2.22
            events.append({"code": code, "time_s": time, "sample": round(time * 1000)})
    return events


def test_brainvision_marker_positions_are_one_based(tmp_path):
    path = tmp_path / "sample.vmrk"
    path.write_text("[Marker Infos]\nMk1=New Segment,,1,1,0\nMk2=Stimulus,S128,1001,1,0\nMk3=Stimulus,S 48,1131,1,0\n")
    parsed = parse_markers(path)
    assert parsed[0]["time_s"] == 1.0
    assert parsed[1]["time_s"] == 1.13
    path.write_text("Mk1=Stimulus,S 99,1001,1,0\n")
    with pytest.raises(ValueError, match="Undocumented"):
        parse_markers(path)


def test_actual_stimulus_timing_defines_blocks_and_holdout():
    blocks = audit_blocks(markers())
    assert [b["role"] for b in blocks] == ["calibration"] * 6 + ["evaluation"] * 3
    assert blocks[0]["task_end_s"] - blocks[0]["task_start_s"] == pytest.approx(44.52)
    assert all(a["slice_end_s"] <= b["slice_start_s"] for a, b in zip(blocks, blocks[1:]))
    broken = markers()
    broken.pop(5)
    with pytest.raises(ValueError, match="20 trials"):
        audit_blocks(broken)


def test_quality_highpass_handles_offsets_without_hiding_artifacts():
    rec, _ = simulate()
    shifted = replace(rec, samples=rec.samples + 500)
    shifted.samples[0, 119 * 128] += 1000  # A fast gross artifact surviving the quality high-pass.
    with pytest.raises(ValueError, match="usable"):
        prepare(shifted, Config())
    result = prepare(shifted, Config(quality_highpass_hz=1.0))
    assert result.bad.mean() < 0.25
    assert result.bad[119 * 128]


def test_erp_epoch_timing_and_baseline():
    from eeg_moments.data import Recording
    from eeg_moments.signal import Prepared

    data = np.tile(np.arange(2000, dtype=float), (2, 1))
    rec = Recording(data, 200, ("A", "B"), "s", "r", "replayed_eeg")
    prepared = Prepared(rec, data[None], np.zeros(2000, dtype=bool))
    epochs, valid = extract_epochs(prepared, [0.0, 2.0, 9.5])
    np.testing.assert_array_equal(valid, [1])
    assert epochs.shape == (1, 2, 220)
    np.testing.assert_allclose(epochs[:, :, :20].mean(axis=-1), 0)
    assert epochs[0, 0, 20] == pytest.approx(10.5)
    features = ERPMeanBins().fit_transform(epochs)
    assert features.shape == (1, 10)
    assert features[0, 0] == pytest.approx(30.0)


def test_metrics_do_not_claim_accuracy_with_one_class_or_no_trials():
    assert classification_metrics([], [])["auroc"] is None
    assert classification_metrics([1, 1], [0.1, 0.2])["auroc"] is None
    result = classification_metrics([0, 0, 1, 1], [-2, -1, 1, 2])
    assert result["auroc"] == result["average_precision"] == 1.0


def test_erp_refuses_raw_input_and_heldout_training():
    from eeg_moments.data import Recording

    recording = Recording(np.ones((28, 2000)), 200, EEG_CHANNELS, "s", "r", "replayed_eeg")
    model = ERPModel("s", "mean_bins", None, {"processing_id": "eog-corrected"})
    with pytest.raises(ValueError, match="ocular preprocessing"):
        model.validate_recording(recording)
    model.validate_recording(replace(recording, processing_id="eog-corrected"))
    block = RealBlock(recording, 7, 2, "evaluation", 0, 1, 9, [], [], np.ones((2, 2000)))
    with pytest.raises(ValueError, match="Evaluation blocks"):
        fit_erp([block])


def test_processing_identity_survives_recording_serialization(tmp_path):
    from eeg_moments.data import Recording

    rec, _ = simulate()
    rec.processing_id = "explicit-preprocessing"
    rec.save(tmp_path / "recording.npz")
    assert Recording.load(tmp_path / "recording.npz").processing_id == rec.processing_id
