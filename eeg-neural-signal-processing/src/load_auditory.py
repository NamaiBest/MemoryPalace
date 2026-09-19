"""Load the PhysioNet auditory EEG-biometric dataset and cache features.

Dataset: 20 subjects x 12 recordings, OpenBCI Ganglion, 4 channels (P4, Cz, F8, T7),
200 Hz, 120 s per recording, already band-passed 1-40 Hz with a 50 Hz notch.

IMPORTANT: all recordings for a subject were made on a SINGLE DAY with one electrode
placement. That means this dataset cannot separate "identifying the person" from
"identifying the electrode placement". See the writeup.
"""
import os, glob, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import features as F

FS = 200.0
CHANNELS = ["P4", "Cz", "F8", "T7"]
DATA = "/Users/namai/Documents/Project/HackMIT/data/auditory/filtered"

# Experiment code -> human label. ex01/ex02 are resting; ex05-ex10 are auditory stimuli.
CONDITIONS = {
    "ex01": "rest_eyes_open",
    "ex02": "rest_eyes_closed",
    "ex05": "inear_native_song",
    "ex06": "inear_nonnative_song",
    "ex07": "inear_neutral_music",
    "ex08": "bone_native_song",
    "ex09": "bone_nonnative_song",
    "ex10": "bone_neutral_music",
}


def parse_name(path):
    b = os.path.basename(path).replace(".csv", "")
    parts = b.split("_")
    subj = int(parts[0][1:])
    ex = parts[1]
    sess = int(parts[2][1:]) if len(parts) > 2 else 1
    return subj, ex, sess, b


def build(epoch_s=4.0, max_uv=None, overlap=0.0):
    """Return dict of arrays: X (n,56), subject, condition, recording, epoch_idx."""
    rows_X, subj, cond, rec, eidx = [], [], [], [], []
    paths = sorted(glob.glob(f"{DATA}/*.csv"))
    for p in paths:
        s, ex, sess, base = parse_name(p)
        df = pd.read_csv(p)
        # columns: index, P4, Cz, F8, T7  -> take the 4 named channels in fixed order
        try:
            x = df[CHANNELS].to_numpy(dtype=np.float64).T
        except KeyError:
            x = df.iloc[:, 1:5].to_numpy(dtype=np.float64).T
        eps = F.epoch_signal(x, FS, epoch_s, overlap=overlap, max_uv=max_uv)
        for i, e in enumerate(eps):
            rows_X.append(F.epoch_features(e, FS))
            subj.append(s); cond.append(CONDITIONS.get(ex, ex)); rec.append(base); eidx.append(i)
    return {
        "X": np.vstack(rows_X),
        "subject": np.array(subj),
        "condition": np.array(cond),
        "recording": np.array(rec),
        "epoch_idx": np.array(eidx),
        "feature_names": np.array(F.feature_names(CHANNELS)),
    }


if __name__ == "__main__":
    epoch_s = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    out = sys.argv[2] if len(sys.argv) > 2 else f"/Users/namai/Documents/Project/HackMIT/data/aud_feat_{int(epoch_s)}s.npz"
    d = build(epoch_s=epoch_s)
    np.savez_compressed(out, **d)
    print(f"X={d['X'].shape} subjects={len(np.unique(d['subject']))} "
          f"recordings={len(np.unique(d['recording']))} conditions={len(np.unique(d['condition']))}")
    print("saved ->", out)
