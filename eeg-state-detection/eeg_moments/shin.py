"""Strict loader for original Shin 2018 dataset A BrainVision recordings."""
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import re

import numpy as np
from scipy.signal import butter, resample_poly, sosfiltfilt

from .data import Recording

EEG_CHANNELS = tuple("Fp1 AFF5h AFz F1 FC5 FC1 T7 C3 Cz CP5 CP1 P7 P3 Pz POz O1 Fp2 AFF6h F2 FC2 FC6 C4 T8 CP2 CP6 P4 P8 O2".split())
FRONTAL = ("Fp1", "Fp2", "AFF5h", "AFF6h", "AFz", "F1", "F2")
RENAMES = {"FP1": "Fp1", "FP2": "Fp2", "AFF5": "AFF5h", "AFF6": "AFF6h"}
BLOCK_CODES = {112: 0, 128: 2, 144: 3}
TRIAL_CODES = {16: (0, 1), 48: (2, 1), 64: (2, 0), 80: (3, 1), 96: (3, 0)}


@dataclass
class RealBlock:
    recording: Recording
    block_index: int
    condition: int
    role: str
    original_offset_s: float
    task_start_s: float
    task_end_s: float
    trials: list[dict]
    baseline_intervals_s: list[list[float]]
    eog: np.ndarray


def parse_markers(path, sample_rate=1000.0):
    events = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not re.match(r"Mk\d+=", line):
            continue
        fields = line.split("=", 1)[1].split(",")
        if fields[0] != "Stimulus":
            continue
        match = re.fullmatch(r"S\s*(\d+)", fields[1])
        if not match:
            raise ValueError(f"Unknown stimulus description: {fields[1]}")
        code = int(match.group(1))
        if code not in BLOCK_CODES and code not in TRIAL_CODES:
            raise ValueError(f"Undocumented stimulus code {code}")
        sample = int(fields[2]) - 1  # BrainVision positions are one-based.
        if sample < 0 or (events and sample < events[-1]["sample"]):
            raise ValueError("Invalid/out-of-order marker position.")
        events.append({"code": code, "sample": sample, "time_s": sample / sample_rate})
    return events


def audit_blocks(events):
    blocks = []
    for event in events:
        if event["code"] in BLOCK_CODES:
            blocks.append({"condition": BLOCK_CODES[event["code"]],
                           "task_start_s": event["time_s"], "trials": []})
        else:
            if not blocks:
                raise ValueError("Trial precedes its task-block marker.")
            condition, label = TRIAL_CODES[event["code"]]
            if condition != blocks[-1]["condition"]:
                raise ValueError("Trial code disagrees with enclosing block condition.")
            blocks[-1]["trials"].append({"time_s": event["time_s"], "label": label, "code": event["code"]})
    if Counter(b["condition"] for b in blocks) != Counter({0: 3, 2: 3, 3: 3}):
        raise ValueError("Expected three blocks per condition in one session.")
    occurrences = Counter()
    for index, block in enumerate(blocks):
        trials = block["trials"]
        if len(trials) != 20:
            raise ValueError("Expected 20 trials per task block; do not silently omit missing events.")
        counts = Counter(t["label"] for t in trials)
        expected = Counter({1: 20}) if block["condition"] == 0 else Counter({1: 6, 0: 14})
        if counts != expected:
            raise ValueError(f"Unexpected trial balance: {counts}")
        times = np.asarray([t["time_s"] for t in trials])
        spacing = np.diff(times)
        if not np.all((spacing >= 1.5) & (spacing <= 3.0)):
            raise ValueError("Unexpected stimulus spacing; review marker mapping.")
        if not 0 <= times[0] - block["task_start_s"] <= 1:
            raise ValueError("Block marker is not adjacent to first stimulus.")
        block["task_end_s"] = float(times[-1] + np.median(spacing))
        block["median_stimulus_interval_s"] = float(np.median(spacing))
        occurrences[block["condition"]] += 1
        block["role"] = "calibration" if occurrences[block["condition"]] <= 2 else "evaluation"
        block["block_index"] = index
        block["slice_start_s"] = round(block["task_start_s"] - 10, 3)
        block["slice_end_s"] = round(block["task_end_s"] + 10, 3)
        if index and block["slice_start_s"] < blocks[index - 1]["slice_end_s"]:
            raise ValueError("Block context overlaps: change protocol before using this recording.")
    if max(b["block_index"] for b in blocks if b["role"] == "calibration") >= min(
            b["block_index"] for b in blocks if b["role"] == "evaluation"):
        raise ValueError("The prespecified split is not chronological in this session.")
    return blocks


def load_session(directory, session=1):
    import mne

    directory = Path(directory)
    header = directory / f"nback{session}.vhdr"
    raw = mne.io.read_raw_brainvision(header, eog=("HEOG", "VEOG"), preload=False, verbose="ERROR")
    if raw.info["sfreq"] != 1000.0:
        raise ValueError("Expected original 1000 Hz BrainVision recording.")
    raw.rename_channels(RENAMES)
    if tuple(raw.ch_names) != EEG_CHANNELS + ("HEOG", "VEOG"):
        raise ValueError(f"Unexpected channels/order: {raw.ch_names}")
    events = parse_markers(directory / f"nback{session}.vmrk", raw.info["sfreq"])
    block_info = audit_blocks(events)
    # Independently verify the importer unit scale against the header's 0.1 uV/int16.
    integers = np.fromfile(directory / f"nback{session}.eeg", dtype="<i2", count=3000).reshape(-1, 30)
    np.testing.assert_allclose(raw.get_data(start=0, stop=len(integers)) * 1e6,
                               integers.T * 0.1, rtol=1e-10, atol=1e-9)
    result = []
    for info in block_info:
        start = round(info["slice_start_s"] * 1000)
        end = round(info["slice_end_s"] * 1000)
        if start < 0 or end > raw.n_times:
            raise ValueError("Requested task context lies outside recording.")
        samples = raw.get_data(start=start, stop=end) * 1e6
        samples = resample_poly(samples, 1, 5, axis=1)
        offset = start / 1000
        rec = Recording(samples[:28], 200.0, EEG_CHANNELS, f"{directory.name}-nback{session}",
                        f"{directory.name}-nback{session}-block{info['block_index'] + 1:02d}", "replayed_eeg")
        task_start, task_end = info["task_start_s"] - offset, info["task_end_s"] - offset
        trials = [{**trial, "time_s": trial["time_s"] - offset} for trial in info["trials"]]
        result.append(RealBlock(rec.validate(), info["block_index"], info["condition"], info["role"],
                                offset, task_start, task_end, trials,
                                [[task_start - 8, task_start - 4], [task_end + 4, task_end + 8]], samples[28:]))
    audit = {"dataset": "Shin2018-A", "participant": directory.name, "session": session,
             "source_url": "https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/",
             "original_sample_rate": 1000, "analysis_sample_rate": 200, "units": "uV",
             "resampling": "scipy.signal.resample_poly, ratio 1/5, default Kaiser anti-alias filter",
             "channels": list(EEG_CHANNELS), "eog_channels": ["HEOG", "VEOG"], "renames": RENAMES,
             "reference": "TP9 per dataset documentation; no rereferencing performed",
             "acquisition_header": header.read_text(), "unit_crosscheck": "MNE volts vs original int16*0.1 uV passed",
             "original_duration_s": raw.n_times / 1000,
             "hashes": {suffix: hashlib.sha256((directory / f"nback{session}.{suffix}").read_bytes()).hexdigest()
                        for suffix in ("eeg", "vhdr", "vmrk")},
             "blocks": block_info}
    return result, audit


def correct_ocular_from_pretask(directory, session, blocks, audit):
    """Fit a fixed EOG projection on a separate pre-task segment, not labeled trials."""
    import mne

    raw = mne.io.read_raw_brainvision(Path(directory) / f"nback{session}.vhdr", preload=False, verbose="ERROR")
    start, end = 2000, round((audit["blocks"][0]["task_start_s"] - 14) * 1000)
    if end - start < 12000 or end >= round(blocks[0].original_offset_s * 1000):
        raise ValueError("No separate pre-task segment is available for ocular calibration.")
    signal = resample_poly(raw.get_data(start=start, stop=end) * 1e6, 1, 5, axis=1)
    signal = sosfiltfilt(butter(4, [1, 30], btype="bandpass", fs=200, output="sos"), signal, axis=1)
    signal = signal[:, 400:-400]  # Trim 2 seconds at both independent segment edges.
    eye = signal[28:]
    covariance = eye @ eye.T
    penalty = np.trace(covariance) * 0.001 / 2
    if penalty <= 0:
        raise ValueError("EOG calibration has no variance.")
    coefficients = np.linalg.solve(covariance + np.eye(2) * penalty, eye @ signal[:28].T).T
    identity = "eog-regression-v1-" + hashlib.sha256(coefficients.tobytes()).hexdigest()
    corrected = [replace(b, recording=replace(b.recording, samples=b.recording.samples - coefficients @ b.eog,
                                              processing_id=identity))
                 for b in blocks]
    audit["ocular_correction"] = {
        "method": "Fixed linear EOG regression estimated on an independent pre-task segment",
        "fit_interval_s": [start / 1000 + 2, end / 1000 - 2], "ridge_relative_trace": 0.001,
        "coefficients": coefficients.tolist(), "processing_id": identity, "fitted_on_task_trials": False,
        "limitations": "May remove EEG correlated with eye signals; does not establish artifact-free neural activity."}
    return corrected, audit
