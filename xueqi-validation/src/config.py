"""Single place for paths, seeds, labels, and preprocessing constants.

Nothing in the other scripts should hard-code event names, channel lists,
filter cutoffs, or the OpenBCI scale factor. If the dataset files contradict
a value here, update this file and DATASET_NOTES.md together.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / "on006394"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = RESULTS_DIR / "cache"

RANDOM_SEED = 42

# Dataset README / channels.tsv: indicated values are 24× too large.
OPENBCI_SCALE_DIVISOR = 24.0

# Sidecar defaults. Loaders still read the JSON and warn on mismatch.
EXPECTED_SFREQ = 125.0
EXPECTED_LINE_FREQ = 50.0
EXPECTED_N_CHANNELS = 16
EXPECTED_REFERENCE = "Left earlobe"
EXPECTED_UNITS = "microV/24"

CHANNEL_NAMES = [
    "Fp1", "C3", "Fp2", "C4", "Fz", "Cz", "O1", "O2",
    "F7", "F8", "F3", "F4", "T7", "T8", "P3", "P4",
]

# events.tsv trial_type values. Do not invent additional codes.
TRIAL_TYPE_SURPRISE = "surprises"
TRIAL_TYPE_CONTROL = "dummy-surprises"
TRIAL_TYPE_PROBE = "probes"
TRIAL_TYPE_DUMMY_PROBE = "dummy-probes"
LABEL_EVENT_TYPES = (TRIAL_TYPE_SURPRISE, TRIAL_TYPE_CONTROL)

# Epoching around surprise / dummy-surprise onsets.
EPOCH_TMIN = -0.20
EPOCH_TMAX = 0.80
BASELINE = (-0.20, 0.00)
FEATURE_WINDOW = (0.00, 0.80)
PREEVENT_FEATURE_WINDOW = (-0.20, 0.00)

# Filter. 50 Hz from sidecar PowerLineFrequency (not 60 Hz).
L_FREQ = 1.0
H_FREQ = 40.0
NOTCH_FREQ = 50.0
NOTCH_WIDTH = 2.0

# Peak-to-peak reject after converting to microvolts.
REJECT_UV = 150.0

# Frequency bands. low_gamma is limited by H_FREQ and 125 Hz sampling.
BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "low_gamma": (30.0, 40.0),
}

# Electrode sets. Names must exist in CHANNEL_NAMES.
# glasses2 = temple sites reachable from blank frames HackMIT stocks.
# This is NOT a claim about Meta Ray-Ban glasses.
CHANNEL_SETS = {
    "all16": CHANNEL_NAMES,
    "half8": ["Fz", "Cz", "F3", "F4", "F7", "F8", "C3", "C4"],
    "ganglion4": ["Fz", "Cz", "F7", "F8"],
    "glasses2": ["F7", "F8"],
}

CHANNEL_SET_NOTES = {
    "all16": "All 16 dataset EEG channels.",
    "half8": "Frontocentral 8-channel subset (surprise / P3a-like coverage).",
    "ganglion4": "4-channel subset in OpenBCI Ganglion-like 10-20 space.",
    "glasses2": "F7/F8 temple pair; plausible on blank eyeglass frames, not Meta Ray-Bans.",
}

# Continuous detector.
STREAM_WINDOW_S = 0.80
STREAM_HOP_S = 0.20
DETECTION_WINDOW_S = 2.00
PERSIST_K_CANDIDATES = [2, 3, 4, 5]
COOLDOWN_S_CANDIDATES = [4.0, 8.0, 15.0]
THRESHOLD_QUANTILES = [0.90, 0.95, 0.99, 0.995]
# Target: keep false triggers from exploding while still detecting events.
TRIGGER_TARGET_MAX_FP_PER_HOUR = 12.0

ERP_CHANNELS = ["Fz", "Cz", "Pz_proxy"]
PZ_PROXY = ["P3", "P4"]  # no Pz in the montage; mean(P3, P4) used in plots

TASKS = ("SiB", "SiD")
TASK_DESCRIPTIONS = {
    "SiB": "Visual surprise task (behavioral condition=v). Inferred: surprise-induced blindness.",
    "SiD": "Auditory surprise task (behavioral condition=a). Inferred: surprise-induced deafness.",
}
