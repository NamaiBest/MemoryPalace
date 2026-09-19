"""Preliminary EEG-biometric experiments on the auditory dataset.

Every split is at the RECORDING level. Adjacent epochs within one recording are
highly correlated, so a random epoch-level split leaks the answer into the training
set and produces meaningless accuracy. E0 demonstrates exactly that.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import evaluation as EV

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split

RNG = 0


def model():
    return make_pipeline(StandardScaler(),
                         LDA(solver="eigen", shrinkage="auto"))


def run_split(d, tr_mask, te_mask, name, chan_idx=None):
    X, y = d["X"], d["subject"]
    Xtr, ytr = X[tr_mask], y[tr_mask]
    Xte, yte = X[te_mask], y[te_mask]
    if chan_idx is not None:
        Xtr, Xte = Xtr[:, chan_idx], Xte[:, chan_idx]
    if len(np.unique(ytr)) < 2 or len(Xte) == 0:
        return None
    m = model().fit(Xtr, ytr)
    proba = m.predict_proba(Xte)
    pred = m.classes_[np.argmax(proba, axis=1)]
    return EV.summarize(name, yte, pred, proba, list(m.classes_))


def channel_indices(feature_names, keep):
    """Select the 14 features belonging to each kept channel."""
    return np.array([i for i, n in enumerate(feature_names) if n.split("_")[0] in keep])


def main(npz):
    d = dict(np.load(npz, allow_pickle=True))
    d["feature_names"] = d["feature_names"].astype(str)
    cond, rec, subj = d["condition"].astype(str), d["recording"].astype(str), d["subject"]
    fn = d["feature_names"]
    results = []
    print(f"\nLoaded {d['X'].shape[0]} epochs, {d['X'].shape[1]} features, "
          f"{len(np.unique(subj))} subjects, {len(np.unique(rec))} recordings\n")
    print("=" * 118)

    # ---- E0: the leakage control -------------------------------------------------
    # Random epoch-level split: epochs from the SAME recording land in train and test.
    idx = np.arange(len(subj))
    tr, te = train_test_split(idx, test_size=0.3, random_state=RNG, stratify=subj)
    m_tr = np.zeros(len(subj), bool); m_tr[tr] = True
    m_te = np.zeros(len(subj), bool); m_te[te] = True
    r = run_split(d, m_tr, m_te, "E0a LEAKY random epoch split (DO NOT TRUST)")
    if r: results.append(r); print(EV.fmt(r))

    # Honest version: hold out whole recordings, stratified by subject.
    rng = np.random.RandomState(RNG)
    held = []
    for s in np.unique(subj):
        rs = np.unique(rec[subj == s])
        held.extend(rng.choice(rs, size=max(1, len(rs) // 4), replace=False))
    m_te = np.isin(rec, held); m_tr = ~m_te
    r = run_split(d, m_tr, m_te, "E0b honest recording-level split")
    if r: results.append(r); print(EV.fmt(r))
    print("-" * 118)

    # ---- E1: within-condition, cross-recording (optimistic) ----------------------
    # Resting eyes-open has 3 recordings/subject: train on 2, test on the 3rd.
    for c in ["rest_eyes_open", "rest_eyes_closed"]:
        m = cond == c
        if m.sum() == 0:
            continue
        sess3 = np.array([r_.endswith("_s03") for r_ in rec])
        r = run_split(d, m & ~sess3, m & sess3, f"E1 {c}: train s01+s02 -> test s03")
        if r: results.append(r); print(EV.fmt(r))
    print("-" * 118)

    # ---- E2: cross-condition (the honest generalization test) --------------------
    rest = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
    aud = ~rest
    r = run_split(d, rest, aud, "E2a train RESTING -> test AUDITORY")
    if r: results.append(r); print(EV.fmt(r))
    r = run_split(d, aud, rest, "E2b train AUDITORY -> test RESTING")
    if r: results.append(r); print(EV.fmt(r))
    eo = cond == "rest_eyes_open"; ec = cond == "rest_eyes_closed"
    r = run_split(d, eo, ec, "E2c train EYES-OPEN -> test EYES-CLOSED")
    if r: results.append(r); print(EV.fmt(r))
    print("-" * 118)

    # ---- E3: per-condition discriminability -------------------------------------
    for c in sorted(np.unique(cond)):
        m = cond == c
        recs = np.unique(rec[m])
        if len(recs) < len(np.unique(subj)) * 2:
            continue  # need >=2 recordings/subject to split by recording
        sess3 = np.array([r_.endswith("_s03") for r_ in rec])
        if (m & sess3).sum() == 0:
            continue
        r = run_split(d, m & ~sess3, m & sess3, f"E3 {c}")
        if r: results.append(r); print(EV.fmt(r))
    print("-" * 118)

    # ---- E4: channel ablation (which electrodes actually carry identity?) --------
    # T7 and F8 are the two positions reachable from an eyeglass frame.
    sets = {
        "ALL 4 (P4,Cz,F8,T7)": ["P4", "Cz", "F8", "T7"],
        "GLASSES-REACHABLE (F8,T7)": ["F8", "T7"],
        "NON-GLASSES (P4,Cz)": ["P4", "Cz"],
        "single T7": ["T7"], "single F8": ["F8"],
        "single Cz": ["Cz"], "single P4": ["P4"],
    }
    for label, keep in sets.items():
        ci = channel_indices(fn, keep)
        r = run_split(d, rest, aud, f"E4 [{label}] rest->auditory", chan_idx=ci)
        if r: results.append(r); print(EV.fmt(r))
    print("=" * 118)
    return results


if __name__ == "__main__":
    npz = sys.argv[1]
    res = main(npz)
    out = sys.argv[2] if len(sys.argv) > 2 else "/Users/namai/Documents/Project/HackMIT/results/auditory.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), indent=2)
    print(f"\nsaved -> {out}")
