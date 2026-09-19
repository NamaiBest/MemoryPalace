"""Neurosity Crown's EXACT 8 channels, tested on real labeled tasks. Not an estimate.

Crown's montage: CP3, C3, F5, PO3, PO4, F6, C4, CP4.

CHANNELS.md in confusion-detector/ estimated Crown performance on the surprise dataset
(ds006394) using nearby substitute electrodes, because that dataset does not contain
F5/F6/CP3/CP4/PO3/PO4. This script does not substitute anything: EEGMMIDB's 64-channel
montage (already downloaded, 109 subjects) contains all 8 Crown channel names exactly.

Two real tasks, both already downloaded:
  - STATE:   R01 (eyes-open) vs R02 (eyes-closed) rest.       109 subjects.
  - COMMAND: R04+R08 -> R12, imagined left vs right fist.     109 subjects.

Neither is "confusion" - no public dataset has that label on this exact montage. This
answers a narrower, still useful question: given electrodes at exactly the positions
Crown puts them, how much signal is there for state and for volitional command?
"""
import os, sys, glob, warnings, json
import numpy as np

warnings.filterwarnings("ignore")
import mne
from mne.decoding import CSP
mne.set_log_level("ERROR")

sys.path.insert(0, os.path.dirname(__file__))
import features as F
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline, Pipeline

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "eegmmidb")
CROWN = ["F5", "F6", "C3", "C4", "Cp3", "Cp4", "Po3", "Po4"]
FS_STATE = 160.0


def norm(c):
    return c.replace(".", "").strip().capitalize()


def model():
    return make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))


# ---------------------------------------------------------------- STATE ----

def load_state(subj, run, picks=CROWN):
    p = f"{DATA}/S{subj:03d}R{run:02d}.edf"
    if not os.path.exists(p):
        return None
    raw = mne.io.read_raw_edf(p, preload=True, verbose=False)
    raw.rename_channels({c: norm(c) for c in raw.ch_names})
    keep = [c for c in picks if c in raw.ch_names]
    if len(keep) < len(picks):
        return None
    raw.pick(keep)
    raw.filter(1., 40., verbose=False)
    raw.notch_filter(60., verbose=False)
    x = raw.get_data() * 1e6
    eps = F.epoch_signal(x, FS_STATE, epoch_s=4.0)
    return np.stack([F.epoch_features(e, FS_STATE) for e in eps]) if eps else None


def run_state(picks, label):
    Xtr_all, ytr_all, Xte_all, yte_all = [], [], [], []
    for s in range(1, 110):
        a = load_state(s, 1, picks)   # eyes-open  -> train
        b = load_state(s, 2, picks)   # eyes-closed -> test
        if a is None or b is None:
            continue
        Xtr_all.append(a); ytr_all += [s] * len(a)
        Xte_all.append(b); yte_all += [s] * len(b)
    if not Xtr_all:
        return None
    Xtr, Xte = np.vstack(Xtr_all), np.vstack(Xte_all)
    ytr, yte = np.array(ytr_all), np.array(yte_all)
    m = model().fit(Xtr, ytr)
    proba = m.predict_proba(Xte)
    pred = m.classes_[np.argmax(proba, axis=1)]
    acc = float(np.mean(pred == yte))
    idx = {c: i for i, c in enumerate(m.classes_)}
    gen, imp = [], []
    for p, yt in zip(proba, yte):
        ti = idx[yt]; gen.append(p[ti]); imp.extend(np.delete(p, ti))
    from sklearn.metrics import roc_curve
    y = np.r_[np.ones(len(gen)), np.zeros(len(imp))]
    sc = np.r_[gen, imp]
    fpr, tpr, _ = roc_curve(y, sc)
    fnr = 1 - tpr
    eer = float((fpr[np.nanargmin(np.abs(fnr - fpr))] +
                fnr[np.nanargmin(np.abs(fnr - fpr))]) / 2)
    print(f"  [STATE {label:<28s}] subj={len(m.classes_):3d}  n={len(yte):5d}  "
          f"rank1={acc*100:6.2f}%  EER={eer*100:6.2f}%  chance={100/len(m.classes_):.2f}%")
    return {"label": label, "n_subjects": len(m.classes_), "rank1_acc": acc, "eer": eer}


# --------------------------------------------------------------- MOTOR -----

def load_mi(subj, runs, picks=CROWN):
    Xs, ys = [], []
    for r in runs:
        p = f"{DATA}/S{subj:03d}R{r:02d}.edf"
        if not os.path.exists(p):
            return None, None
        raw = mne.io.read_raw_edf(p, preload=True, verbose=False)
        raw.rename_channels({c: norm(c) for c in raw.ch_names})
        keep = [c for c in picks if c in raw.ch_names]
        if len(keep) < len(picks):
            return None, None
        raw.pick(keep)
        raw.filter(7., 30., verbose=False)
        ev, eid = mne.events_from_annotations(raw, verbose=False)
        want = {k: v for k, v in eid.items() if k in ("T1", "T2")}
        if len(want) < 2:
            continue
        ep = mne.Epochs(raw, ev, want, tmin=0.5, tmax=3.5, baseline=None,
                        preload=True, verbose=False)
        if len(ep) == 0:
            continue
        Xs.append(ep.get_data())
        ys.append(np.array([1 if e == want.get("T2") else 0 for e in ep.events[:, 2]]))
    if not Xs:
        return None, None
    return np.concatenate(Xs), np.concatenate(ys)


def run_mi(picks, label, n_comp=4):
    accs = []
    for s in range(1, 110):
        Xtr, ytr = load_mi(s, [4, 8], picks)
        Xte, yte = load_mi(s, [12], picks)
        if Xtr is None or Xte is None or len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
            continue
        try:
            clf = Pipeline([("csp", CSP(n_components=min(n_comp, len(picks)), log=True)),
                            ("lda", LDA(solver="eigen", shrinkage="auto"))])
            clf.fit(Xtr, ytr)
            accs.append(clf.score(Xte, yte))
        except Exception:
            continue
    a = np.array(accs)
    lit = float(np.mean(a >= 0.70))
    print(f"  [COMMAND {label:<26s}] n={len(a):3d} subj  mean={a.mean()*100:5.2f}% "
          f"+/-{a.std()*100:4.2f}  median={np.median(a)*100:5.2f}%  >=70%: {lit*100:4.1f}%")
    return {"label": label, "n_subjects": len(a), "mean": float(a.mean()),
            "std": float(a.std()), "median": float(np.median(a)), "frac_above_70": lit}


if __name__ == "__main__":
    print("=" * 100)
    print("NEUROSITY CROWN, EXACT 8 CHANNELS (F5 F6 C3 C4 CP3 CP4 PO3 PO4)")
    print("Real labeled tasks, 109 subjects, EEGMMIDB. No channel substitution.")
    print("=" * 100)
    out = {}

    print("\n-- STATE: eyes-open -> eyes-closed --")
    out["state_crown8"] = run_state(CROWN, "Crown-exact (F5 F6 C3 C4 CP3 CP4 PO3 PO4)")
    out["state_all64"] = run_state(None if False else
        ["Fc5","Fc3","Fc1","Fcz","Fc2","Fc4","Fc6","C5","C3","C1","Cz","C2","C4","C6",
         "Cp5","Cp3","Cp1","Cpz","Cp2","Cp4","Cp6","Fp1","Fpz","Fp2","Af7","Af3","Afz",
         "Af4","Af8","F7","F5","F3","F1","Fz","F2","F4","F6","Ft7","Ft8","T7","T8","T9",
         "T10","Tp7","Tp8","P7","P5","P3","P1","Pz","P2","P4","P6","P8","Po7","Po3",
         "Poz","Po4","Po8","O1","Oz","O2","Iz"], "all 64 (reference ceiling)")

    print("\n-- COMMAND: imagined left vs right fist --")
    out["mi_crown8"] = run_mi(CROWN, "Crown-exact")

    os.makedirs("../results", exist_ok=True) if False else None
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "results"),
                exist_ok=True)
    outp = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "results", "crown_exact.json")
    json.dump(out, open(outp, "w"), indent=2)
    print(f"\nsaved -> {outp}")
