"""Load BIDS EEGLAB recordings, correct OpenBCI scaling, filter, epoch.

Raw .set/.fdt files are never overwritten. Processed epochs go to results/cache/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.extract_events import events_for_recording  # noqa: E402
from src.io_utils import ensure_dirs, log_skip, reset_skipped, setup_logging  # noqa: E402

LOG = None


def _log():
    global LOG
    if LOG is None:
        LOG = setup_logging("preprocess")
    return LOG


def list_recordings() -> list[dict]:
    rows = []
    for subdir in sorted(C.DATASET_ROOT.glob("sub-*")):
        subject = subdir.name
        for task in C.TASKS:
            set_path = subdir / "eeg" / f"{subject}_task-{task}_eeg.set"
            fdt_path = subdir / "eeg" / f"{subject}_task-{task}_eeg.fdt"
            ev_path = subdir / "eeg" / f"{subject}_task-{task}_events.tsv"
            js_path = subdir / "eeg" / f"{subject}_task-{task}_eeg.json"
            ch_path = subdir / "eeg" / f"{subject}_task-{task}_channels.tsv"
            rows.append(
                {
                    "subject": subject,
                    "task": task,
                    "set_path": set_path,
                    "fdt_path": fdt_path,
                    "events_path": ev_path,
                    "json_path": js_path,
                    "channels_path": ch_path,
                }
            )
    return rows


def load_raw(rec: dict):
    """Load one EEGLAB recording, scale to µV, bandpass + notch.

    Returns mne.io.Raw or None if the file cannot be used.
    """
    import mne

    log = _log()
    if not rec["set_path"].exists() or not rec["fdt_path"].exists():
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "preprocess",
                "reason": "missing_eeg_file",
                "set": rec["set_path"].exists(),
                "fdt": rec["fdt_path"].exists(),
            }
        )
        return None
    if rec["json_path"].exists():
        meta = json.loads(rec["json_path"].read_text())
        sfreq = float(meta.get("SamplingFrequency", C.EXPECTED_SFREQ))
        line = meta.get("PowerLineFrequency")
        nch = meta.get("EEGChannelCount")
        if sfreq != C.EXPECTED_SFREQ:
            log.warning(
                "%s %s SamplingFrequency=%s (expected %s)",
                rec["subject"], rec["task"], sfreq, C.EXPECTED_SFREQ,
            )
        if line != C.EXPECTED_LINE_FREQ:
            log.warning(
                "%s %s PowerLineFrequency=%s (expected %s)",
                rec["subject"], rec["task"], line, C.EXPECTED_LINE_FREQ,
            )
        if nch != C.EXPECTED_N_CHANNELS:
            log.warning(
                "%s %s EEGChannelCount=%s (expected %s)",
                rec["subject"], rec["task"], nch, C.EXPECTED_N_CHANNELS,
            )

    try:
        raw = mne.io.read_raw_eeglab(rec["set_path"], preload=True, verbose="ERROR")
    except Exception as exc:  # noqa: BLE001 — must log, not swallow
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "preprocess",
                "reason": "eeglab_load_failed",
                "error": repr(exc),
            }
        )
        return None

    raw.rename_channels({n: n.strip() for n in raw.ch_names})
    missing = [ch for ch in C.CHANNEL_NAMES if ch not in raw.ch_names]
    if missing:
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "preprocess",
                "reason": "unexpected_channel_names",
                "missing": missing,
                "found": raw.ch_names,
            }
        )
        return None
    raw.pick(C.CHANNEL_NAMES)

    # Author-documented OpenBCI GUI v5.0.1 scale error.
    # MNE already converted EEGLAB µV storage into volts. Do not scale by 1e-6 again.
    raw.apply_function(lambda x: x / C.OPENBCI_SCALE_DIVISOR, picks="eeg", channel_wise=True)

    raw.filter(l_freq=C.L_FREQ, h_freq=C.H_FREQ, picks="eeg", verbose="ERROR")
    raw.notch_filter(freqs=[C.NOTCH_FREQ], picks="eeg", verbose="ERROR")
    try:
        raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    except Exception:
        pass
    return raw


def epoch_recording(raw, rec: dict) -> dict | None:
    """Cut surprise vs dummy-surprise epochs. Returns a dict of arrays or None."""
    import mne

    log = _log()
    events_df, skip_reason = events_for_recording(rec, raw.times[-1])
    if skip_reason:
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "epoch",
                "reason": skip_reason,
            }
        )
        return None
    if events_df is None or events_df.empty:
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "epoch",
                "reason": "no_usable_events",
            }
        )
        return None

    sfreq = float(raw.info["sfreq"])
    id_map = {C.TRIAL_TYPE_CONTROL: 0, C.TRIAL_TYPE_SURPRISE: 1}
    mne_events = []
    for _, row in events_df.iterrows():
        sample = int(np.round(row["onset"] * sfreq))
        if sample < 0 or sample >= raw.n_times:
            log.warning(
                "%s %s event onset %.3f outside recording (n_times=%s); dropped",
                rec["subject"], rec["task"], row["onset"], raw.n_times,
            )
            continue
        mne_events.append([sample, 0, id_map[row["trial_type"]]])
    if not mne_events:
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "epoch",
                "reason": "all_events_outside_recording",
            }
        )
        return None
    mne_events = np.array(mne_events, dtype=int)

    reject = dict(eeg=C.REJECT_UV * 1e-6)  # MNE raw is in volts; 150 µV

    epochs = mne.Epochs(
        raw,
        mne_events,
        event_id={"control": 0, "surprise": 1},
        tmin=C.EPOCH_TMIN,
        tmax=C.EPOCH_TMAX,
        baseline=C.BASELINE,
        preload=True,
        reject=reject,
        verbose="ERROR",
    )
    n_in = len(mne_events)
    n_keep = len(epochs)
    n_drop = n_in - n_keep
    log.info(
        "%s %s epochs kept %s / %s (dropped %s artifact or edge)",
        rec["subject"], rec["task"], n_keep, n_in, n_drop,
    )
    if n_keep == 0:
        log_skip(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "stage": "epoch",
                "reason": "all_epochs_rejected",
                "n_in": n_in,
            }
        )
        return None

    data_uv = epochs.get_data() * 1e6  # back to µV for features/plots
    return {
        "subject": rec["subject"],
        "task": rec["task"],
        "data": data_uv.astype(np.float32),  # (n_epochs, n_ch, n_times)
        "labels": epochs.events[:, 2].astype(np.int8),
        "times": epochs.times.astype(np.float32),
        "ch_names": list(epochs.ch_names),
        "sfreq": np.float32(sfreq),
        "n_in": n_in,
        "n_keep": n_keep,
        "n_drop": n_drop,
        "duration_s": float(raw.times[-1]),
        "onsets": events_df["onset"].to_numpy(dtype=np.float64),
        "onset_types": events_df["trial_type"].to_numpy(),
    }


def cache_path(subject: str, task: str) -> Path:
    return C.CACHE_DIR / f"{subject}_{task}_epochs.npz"


def save_epochs(pack: dict) -> Path:
    path = cache_path(pack["subject"], pack["task"])
    np.savez_compressed(
        path,
        data=pack["data"],
        labels=pack["labels"],
        times=pack["times"],
        ch_names=np.array(pack["ch_names"]),
        sfreq=pack["sfreq"],
        n_in=pack["n_in"],
        n_keep=pack["n_keep"],
        n_drop=pack["n_drop"],
        duration_s=pack["duration_s"],
        onsets=pack["onsets"],
        onset_types=pack["onset_types"].astype("U32"),
        subject=np.array(pack["subject"]),
        task=np.array(pack["task"]),
    )
    return path


def load_epochs(subject: str, task: str) -> dict | None:
    path = cache_path(subject, task)
    if not path.exists():
        return None
    z = np.load(path, allow_pickle=False)
    return {
        "subject": str(z["subject"]),
        "task": str(z["task"]),
        "data": z["data"],
        "labels": z["labels"],
        "times": z["times"],
        "ch_names": [str(x) for x in z["ch_names"]],
        "sfreq": float(z["sfreq"]),
        "n_in": int(z["n_in"]),
        "n_keep": int(z["n_keep"]),
        "n_drop": int(z["n_drop"]),
        "duration_s": float(z["duration_s"]),
        "onsets": z["onsets"],
        "onset_types": z["onset_types"].astype(str),
    }


def iter_cached_epochs():
    for rec in list_recordings():
        pack = load_epochs(rec["subject"], rec["task"])
        if pack is not None:
            yield pack


def run(force: bool = False) -> list[dict]:
    log = _log()
    ensure_dirs()
    if force:
        reset_skipped()
    summary = []
    for rec in list_recordings():
        dest = cache_path(rec["subject"], rec["task"])
        if dest.exists() and not force:
            log.info("cache hit %s", dest.name)
            z = np.load(dest)
            summary.append(
                {
                    "subject": rec["subject"],
                    "task": rec["task"],
                    "n_keep": int(z["n_keep"]),
                    "n_drop": int(z["n_drop"]),
                    "cached": True,
                }
            )
            continue
        raw = load_raw(rec)
        if raw is None:
            continue
        pack = epoch_recording(raw, rec)
        del raw
        if pack is None:
            continue
        save_epochs(pack)
        summary.append(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "n_keep": pack["n_keep"],
                "n_drop": pack["n_drop"],
                "n_surprise": int((pack["labels"] == 1).sum()),
                "n_control": int((pack["labels"] == 0).sum()),
                "cached": False,
            }
        )
    from src.io_utils import write_json

    write_json(C.RESULTS_DIR / "preprocess_summary.json", summary)
    log.info("preprocessed %s recordings", len(summary))
    return summary


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
