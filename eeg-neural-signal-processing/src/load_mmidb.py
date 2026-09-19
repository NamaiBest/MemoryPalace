"""Load PhysioNet EEG Motor Movement/Imagery baseline runs and cache features.

R01 = baseline, eyes open. R02 = baseline, eyes closed. 1 minute each, 64 channels,
160 Hz. 109 subjects -> this is the scale test.

Same caveat as the auditory set, and worse: both runs come from ONE session with one
cap placement, so cross-run accuracy here is an upper bound, not a deployment number.
"""
import os, glob, sys, warnings
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import features as F

warnings.filterwarnings("ignore")
import mne
mne.set_log_level("ERROR")

DATA = "/Users/namai/Documents/Project/HackMIT/data/eegmmidb"
FS = 160.0

# 10-10 subset roughly matching what a wearable can reach, plus standard references.
# EEGMMIDB uses the BCI2000 naming (Fc5., C3.., etc) - we normalise below.
GLASSES_LIKE = ["Af7", "Af8", "Fp1", "Fp2", "F7", "F8", "T7", "T8"]
CONSUMER8 = ["Fp1", "Fp2", "F7", "F8", "T7", "T8", "O1", "O2"]


def norm(ch):
    return ch.replace(".", "").strip().capitalize()


def build(epoch_s=4.0, subjects=None, picks=None):
    rows_X, subj, run, eidx = [], [], [], []
    paths = sorted(glob.glob(f"{DATA}/*.edf"))
    ch_used = None
    for p in paths:
        b = os.path.basename(p)
        s = int(b[1:4]); r = int(b[5:7])
        if subjects is not None and s not in subjects:
            continue
        try:
            raw = mne.io.read_raw_edf(p, preload=True, verbose=False)
        except Exception:
            continue
        raw.rename_channels({c: norm(c) for c in raw.ch_names})
        if picks is not None:
            keep = [c for c in picks if c in raw.ch_names]
            if len(keep) < len(picks):
                continue
            raw.pick(keep)
        raw.filter(1., 40., verbose=False)
        raw.notch_filter(60., verbose=False)   # US mains
        x = raw.get_data() * 1e6               # V -> uV
        if ch_used is None:
            ch_used = raw.ch_names
        for i, e in enumerate(F.epoch_signal(x, FS, epoch_s)):
            rows_X.append(F.epoch_features(e, FS))
            subj.append(s); run.append(r); eidx.append(i)
    return {
        "X": np.vstack(rows_X),
        "subject": np.array(subj),
        "run": np.array(run),
        "epoch_idx": np.array(eidx),
        "feature_names": np.array(F.feature_names(ch_used)),
        "channels": np.array(ch_used),
    }


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "consumer8"
    picks = {"consumer8": CONSUMER8, "glasses": GLASSES_LIKE, "all": None}[mode]
    d = build(epoch_s=4.0, picks=picks)
    out = f"/Users/namai/Documents/Project/HackMIT/data/mmidb_feat_{mode}.npz"
    np.savez_compressed(out, **d)
    print(f"X={d['X'].shape} subjects={len(np.unique(d['subject']))} "
          f"channels={list(d['channels'])}")
    print("saved ->", out)
