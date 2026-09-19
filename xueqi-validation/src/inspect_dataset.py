#!/usr/bin/env python3
"""Inventory the local on006394 copy. Prints a report and writes results/dataset_inventory.json.

Does not load the large EEG arrays. Safe to run first.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Allow `python src/inspect_dataset.py` from the project folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402


def _read_tsv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main() -> None:
    log = setup_logging("inspect")
    ensure_dirs()
    root = C.DATASET_ROOT
    if not root.exists():
        raise SystemExit(f"Dataset not found: {root}")

    participants = _read_tsv(root / "participants.tsv")
    desc = json.loads((root / "dataset_description.json").read_text())
    readme = (root / "README.md").read_text()

    subjects = sorted(p.name for p in root.glob("sub-*") if p.is_dir())
    trial_types = Counter()
    by_task = defaultdict(Counter)
    recordings = []
    channel_tables = set()
    sidecar_keys = Counter()

    for sub in subjects:
        subdir = root / sub
        for task in C.TASKS:
            rec = {
                "subject": sub,
                "task": task,
                "eeg_set": (subdir / "eeg" / f"{sub}_task-{task}_eeg.set").exists(),
                "eeg_fdt": (subdir / "eeg" / f"{sub}_task-{task}_eeg.fdt").exists(),
                "eeg_json": (subdir / "eeg" / f"{sub}_task-{task}_eeg.json").exists(),
                "channels": (subdir / "eeg" / f"{sub}_task-{task}_channels.tsv").exists(),
                "events": (subdir / "eeg" / f"{sub}_task-{task}_events.tsv").exists(),
                "beh": (subdir / "beh" / f"{sub}_task-{task}_beh.tsv").exists(),
            }
            ev_path = subdir / "eeg" / f"{sub}_task-{task}_events.tsv"
            if rec["events"]:
                rows = _read_tsv(ev_path)
                c = Counter(r["trial_type"] for r in rows)
                rec["n_events"] = len(rows)
                rec["trial_types"] = dict(c)
                rec["onset_min"] = min(float(r["onset"]) for r in rows) if rows else None
                rec["onset_max"] = max(float(r["onset"]) for r in rows) if rows else None
                trial_types.update(c)
                by_task[task].update(c)
            ch_path = subdir / "eeg" / f"{sub}_task-{task}_channels.tsv"
            if rec["channels"]:
                ch_rows = _read_tsv(ch_path)
                channel_tables.add(
                    tuple((r["name"], r["type"], r["units"]) for r in ch_rows)
                )
            js_path = subdir / "eeg" / f"{sub}_task-{task}_eeg.json"
            if rec["eeg_json"]:
                meta = json.loads(js_path.read_text())
                rec["sampling_frequency"] = meta.get("SamplingFrequency")
                rec["reference"] = meta.get("EEGReference")
                rec["line_freq"] = meta.get("PowerLineFrequency")
                rec["n_channels"] = meta.get("EEGChannelCount")
                sidecar_keys[
                    (
                        meta.get("SamplingFrequency"),
                        meta.get("EEGReference"),
                        meta.get("PowerLineFrequency"),
                        meta.get("EEGChannelCount"),
                    )
                ] += 1
            recordings.append(rec)

    inventory = {
        "dataset_name": desc.get("Name"),
        "bids_version": desc.get("BIDSVersion"),
        "license": desc.get("License"),
        "n_participants_tsv": len(participants),
        "n_subject_dirs": len(subjects),
        "subjects": subjects,
        "n_eeg_set": sum(1 for r in recordings if r["eeg_set"]),
        "n_events_files": sum(1 for r in recordings if r["events"]),
        "trial_types_total": dict(trial_types),
        "trial_types_by_task": {k: dict(v) for k, v in by_task.items()},
        "unique_channel_tables": len(channel_tables),
        "channel_names": [row[0] for row in next(iter(channel_tables))] if channel_tables else [],
        "channel_units": [row[2] for row in next(iter(channel_tables))] if channel_tables else [],
        "sidecar_uniques": {str(k): v for k, v in sidecar_keys.items()},
        "readme": readme,
        "recordings": recordings,
        "label_contract": {
            "positive": C.TRIAL_TYPE_SURPRISE,
            "negative": C.TRIAL_TYPE_CONTROL,
            "ignored": [C.TRIAL_TYPE_PROBE, C.TRIAL_TYPE_DUMMY_PROBE],
        },
        "openbci_scale_divisor": C.OPENBCI_SCALE_DIVISOR,
    }
    out = C.RESULTS_DIR / "dataset_inventory.json"
    write_json(out, inventory)

    log.info("Participants: %s", len(subjects))
    log.info("EEG .set files: %s", inventory["n_eeg_set"])
    log.info("Event files: %s", inventory["n_events_files"])
    log.info("trial_type totals: %s", dict(trial_types))
    log.info("Channel names: %s", inventory["channel_names"])
    log.info("Sidecar uniques: %s", dict(sidecar_keys))
    log.info("Wrote %s", out)

    print("\nMissing EEG or events:")
    for r in recordings:
        if not (r["eeg_set"] and r["eeg_fdt"] and r["events"]):
            print(
                f"  {r['subject']} {r['task']}: set={r['eeg_set']} "
                f"fdt={r['eeg_fdt']} events={r['events']}"
            )


if __name__ == "__main__":
    main()
