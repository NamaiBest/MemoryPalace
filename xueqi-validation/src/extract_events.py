"""Read BIDS events.tsv and keep only dataset-provided surprise labels.

Labels are never rewritten. Unknown trial_type values are logged and dropped.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402


def read_events_tsv(path: Path) -> pd.DataFrame:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["onset"] = df["onset"].astype(float)
    df["duration"] = df["duration"].astype(float)
    return df


def events_for_recording(rec: dict, rec_duration_s: float) -> tuple[pd.DataFrame | None, str | None]:
    """Return (events_df, skip_reason).

    events_df contains only surprises / dummy-surprises whose onset is inside
    the recording. skip_reason is a string if the file cannot be used.
    """
    path = rec["events_path"]
    if not path.exists():
        return None, "missing_events_tsv"
    df = read_events_tsv(path)
    if df.empty:
        return None, "empty_events_tsv"
    unknown = sorted(set(df["trial_type"]) - set(C.LABEL_EVENT_TYPES) - {C.TRIAL_TYPE_PROBE, C.TRIAL_TYPE_DUMMY_PROBE})
    if unknown:
        # Do not invent mappings. Keep going but report.
        pass
    keep = df[df["trial_type"].isin(C.LABEL_EVENT_TYPES)].copy()
    if keep.empty:
        return None, "no_surprise_or_dummy_surprise_events"
    n_before = len(keep)
    keep = keep[(keep["onset"] >= 0) & (keep["onset"] <= rec_duration_s)].copy()
    n_outside = n_before - len(keep)
    if n_outside:
        keep.attrs["n_outside"] = n_outside
    if keep.empty:
        return None, "all_label_events_outside_recording"
    if (keep["trial_type"] == C.TRIAL_TYPE_SURPRISE).sum() == 0:
        return None, "no_surprise_events"
    if (keep["trial_type"] == C.TRIAL_TYPE_CONTROL).sum() == 0:
        return None, "no_control_events"
    return keep.reset_index(drop=True), None


def summarize_all() -> dict:
    from src.preprocess import list_recordings

    log = setup_logging("extract_events")
    ensure_dirs()
    counts = []
    for rec in list_recordings():
        if not rec["events_path"].exists():
            counts.append(
                {
                    "subject": rec["subject"],
                    "task": rec["task"],
                    "status": "missing_events_tsv",
                }
            )
            continue
        df = read_events_tsv(rec["events_path"])
        vc = df["trial_type"].value_counts().to_dict() if not df.empty else {}
        counts.append(
            {
                "subject": rec["subject"],
                "task": rec["task"],
                "status": "ok",
                "n": int(len(df)),
                "trial_types": vc,
                "onset_min": float(df["onset"].min()) if len(df) else None,
                "onset_max": float(df["onset"].max()) if len(df) else None,
            }
        )
    out = {
        "label_contract": {
            "positive": C.TRIAL_TYPE_SURPRISE,
            "negative": C.TRIAL_TYPE_CONTROL,
            "note": "Values taken from events.tsv trial_type. Not recoded.",
        },
        "recordings": counts,
    }
    write_json(C.RESULTS_DIR / "event_summary.json", out)
    log.info("wrote event_summary.json (%s recordings)", len(counts))
    return out


def main() -> None:
    summarize_all()


if __name__ == "__main__":
    main()
