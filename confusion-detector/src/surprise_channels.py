"""Is 2 channels enough? Within-subject surprise detection on ds006394.

WHY THIS IS NOT A REPEAT OF "Xueqi's Idea".

That analysis evaluated leave-one-SUBJECT-out: train on other people, test on a new
person with no calibration. It found 2 temple channels (F7/F8) at AUC 0.599, barely
above chance, and its own §14 flags the gap: "Cross-subject transfer is the hard
setting. A same-day wearer-calibrated model might do better and was not the primary
test here."

That untested setting is exactly the product. You put the headband on, it calibrates to
you, and it detects for you. So here we evaluate WITHIN subject:

  (a) within-task  - stratified CV over that person's own trials
  (b) cross-task   - train on their visual task, test on their auditory task
                     (harder: different modality, later in the session)

And rather than assuming F7/F8 is the right pair, we search all 120 electrode pairs and
ask where the glasses-reachable ones rank.

Glasses-reachable on this montage: Fp1, Fp2 (brow ridge / nose pads), F7, F8 (temples),
T7, T8 (behind the temple arm).
"""
import os, sys, json, glob, warnings
import numpy as np

warnings.filterwarnings("ignore")
import mne
mne.set_log_level("ERROR")

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, balanced_accuracy_score

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ds006394")
FS = 125.0
SCALE = 24.0            # dataset README: stored values are 24x too large
TMIN, TMAX = -0.2, 0.8
REJECT_UV = 150.0

GLASSES = {"Fp1", "Fp2", "F7", "F8", "T7", "T8"}
SETS = {
    "all16": None,
    "ganglion4 (Fz Cz F7 F8)": ["Fz", "Cz", "F7", "F8"],
    "glasses4 (Fp1 Fp2 F7 F8)": ["Fp1", "Fp2", "F7", "F8"],
    "glasses2 temples (F7 F8)": ["F7", "F8"],
    "glasses2 brow (Fp1 Fp2)": ["Fp1", "Fp2"],
    "central2 (Fz Cz)": ["Fz", "Cz"],
    # Neurosity Crown is fixed at CP3 C3 F5 PO3 PO4 F6 C4 CP4. This montage has no
    # F5/F6/CP/PO, so approximate: F3/F4 for F5/F6 (F5 sits between F3 and F7),
    # P3/P4 for CP3/CP4, O1/O2 for PO3/PO4. C3/C4 are exact.
    "crown8-like (F3 F4 C3 C4 P3 P4 O1 O2)": ["F3", "F4", "C3", "C4",
                                              "P3", "P4", "O1", "O2"],
    "crown-frontal2 (F3 F4)": ["F3", "F4"],
}


def model():
    return make_pipeline(StandardScaler(),
                         LogisticRegression(max_iter=2000, class_weight="balanced"))


def load_epochs(sub, task):
    """Return (X, y, ch_names) for one subject+task, or None."""
    d = f"{DATA}/{sub}/eeg"
    st = f"{d}/{sub}_task-{task}_eeg.set"
    ev = f"{d}/{sub}_task-{task}_events.tsv"
    if not (os.path.exists(st) and os.path.exists(ev)):
        return None
    try:
        raw = mne.io.read_raw_eeglab(st, preload=True, verbose=False)
    except Exception:
        return None
    if any(c.startswith("EEG ") for c in raw.ch_names):
        return None                      # anonymous channel names, unusable
    raw._data /= SCALE
    raw.filter(1., 40., verbose=False)
    raw.notch_filter(50., verbose=False)

    import csv
    onsets, labels = [], []
    with open(ev) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            tt = (row.get("trial_type") or "").strip()
            if tt in ("surprises", "dummy-surprises"):
                onsets.append(float(row["onset"]))
                labels.append(1 if tt == "surprises" else 0)
    if len(set(labels)) < 2:
        return None

    sf = raw.info["sfreq"]
    events = np.c_[(np.array(onsets) * sf).astype(int),
                   np.zeros(len(onsets), int), np.array(labels) + 1]
    ep = mne.Epochs(raw, events, {"ctrl": 1, "surp": 2}, tmin=TMIN, tmax=TMAX,
                    baseline=(TMIN, 0), preload=True, verbose=False,
                    reject={"eeg": REJECT_UV * 1e-6})
    if len(ep) < 30:
        return None
    y = (ep.events[:, 2] == 2).astype(int)
    if y.sum() < 5 or (1 - y).sum() < 5:
        return None
    return ep.get_data() * 1e6, y, ep.ch_names


def features(X, fs=FS):
    """Compact ERP + band features per channel. Post-onset window only."""
    n0 = int(abs(TMIN) * fs)
    post = X[:, :, n0:]
    out = [post.mean(-1), post.std(-1), post.max(-1), post.min(-1),
           np.abs(post).max(-1), np.sqrt((post ** 2).mean(-1)),
           post.argmax(-1) / fs, post.argmin(-1) / fs]
    # mean amplitude in three latency bands - where an ERP lives
    for a, b in ((0.10, 0.25), (0.25, 0.45), (0.45, 0.70)):
        out.append(post[:, :, int(a * fs):int(b * fs)].mean(-1))
    return np.concatenate(out, axis=1)


def pick(X, ch_names, keep):
    if keep is None:
        return X
    idx = [ch_names.index(c) for c in keep if c in ch_names]
    return X[:, idx, :] if idx else None


def eval_within_task(X, y, n_splits=5):
    """Stratified CV over one person's own trials."""
    F = features(X)
    n_pos = int(y.sum())
    k = min(n_splits, n_pos, int((1 - y).sum()))
    if k < 3:
        return None
    aucs, bas = [], []
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=42).split(F, y):
        if len(np.unique(y[te])) < 2:
            continue
        m = model().fit(F[tr], y[tr])
        p = m.predict_proba(F[te])[:, 1]
        aucs.append(roc_auc_score(y[te], p))
        bas.append(balanced_accuracy_score(y[te], m.predict(F[te])))
    return (float(np.mean(aucs)), float(np.mean(bas))) if aucs else None


def eval_cross_task(Xa, ya, Xb, yb):
    """Train on one task, test on the other. Same person, different modality."""
    Fa, Fb = features(Xa), features(Xb)
    if len(np.unique(ya)) < 2 or len(np.unique(yb)) < 2:
        return None
    m = model().fit(Fa, ya)
    p = m.predict_proba(Fb)[:, 1]
    return (float(roc_auc_score(yb, p)),
            float(balanced_accuracy_score(yb, m.predict(Fb))))


def main():
    subs = sorted({os.path.basename(p) for p in glob.glob(f"{DATA}/sub-*")})
    print(f"subjects on disk: {len(subs)}")
    cache = {}
    for s in subs:
        for t in ("SiB", "SiD"):
            r = load_epochs(s, t)
            if r:
                cache[(s, t)] = r
    print(f"usable recordings: {len(cache)}\n")
    if not cache:
        print("no usable recordings - is the download finished?")
        return

    ch_names = next(iter(cache.values()))[2]
    results = {"within_task": {}, "cross_task": {}, "pairs": {}}

    print("=" * 96)
    print("  WITHIN-SUBJECT, WITHIN-TASK (stratified CV on that person's own trials)")
    print("=" * 96)
    print(f"  {'channel set':<28s} {'n':>4s} {'mean AUC':>9s} {'sd':>6s} "
          f"{'median':>7s} {'>=0.70':>7s}")
    for name, keep in SETS.items():
        aucs = []
        for (s, t), (X, y, cn) in cache.items():
            Xs = pick(X, cn, keep)
            if Xs is None:
                continue
            r = eval_within_task(Xs, y)
            if r:
                aucs.append(r[0])
        if not aucs:
            continue
        a = np.array(aucs)
        results["within_task"][name] = {"n": len(a), "mean": float(a.mean()),
                                        "sd": float(a.std()), "median": float(np.median(a)),
                                        "frac_ge_70": float((a >= 0.70).mean())}
        print(f"  {name:<28s} {len(a):>4d} {a.mean():>9.3f} {a.std():>6.3f} "
              f"{np.median(a):>7.3f} {(a>=0.70).mean()*100:>6.1f}%")

    print()
    print("=" * 96)
    print("  WITHIN-SUBJECT, CROSS-TASK (train visual SiB -> test auditory SiD)")
    print("=" * 96)
    print(f"  {'channel set':<28s} {'n':>4s} {'mean AUC':>9s} {'sd':>6s} {'>=0.70':>7s}")
    for name, keep in SETS.items():
        aucs = []
        for s in subs:
            if (s, "SiB") not in cache or (s, "SiD") not in cache:
                continue
            Xa, ya, cn = cache[(s, "SiB")]
            Xb, yb, _ = cache[(s, "SiD")]
            A, B = pick(Xa, cn, keep), pick(Xb, cn, keep)
            if A is None or B is None:
                continue
            r = eval_cross_task(A, ya, B, yb)
            if r:
                aucs.append(r[0])
        if not aucs:
            continue
        a = np.array(aucs)
        results["cross_task"][name] = {"n": len(a), "mean": float(a.mean()),
                                       "sd": float(a.std()),
                                       "frac_ge_70": float((a >= 0.70).mean())}
        print(f"  {name:<28s} {len(a):>4d} {a.mean():>9.3f} {a.std():>6.3f} "
              f"{(a>=0.70).mean()*100:>6.1f}%")

    print()
    print("=" * 96)
    print("  ALL 2-CHANNEL PAIRS, RANKED (within-task). * = both glasses-reachable")
    print("=" * 96)
    pair_scores = {}
    for i in range(len(ch_names)):
        for j in range(i + 1, len(ch_names)):
            pair = (ch_names[i], ch_names[j])
            aucs = []
            for (s, t), (X, y, cn) in cache.items():
                Xs = pick(X, cn, list(pair))
                if Xs is None:
                    continue
                r = eval_within_task(Xs, y)
                if r:
                    aucs.append(r[0])
            if aucs:
                pair_scores["+".join(pair)] = float(np.mean(aucs))
    results["pairs"] = pair_scores
    ranked = sorted(pair_scores.items(), key=lambda kv: -kv[1])
    for rank, (p, a) in enumerate(ranked[:12], 1):
        gl = "*" if all(c in GLASSES for c in p.split("+")) else " "
        print(f"  {rank:>2d}. {gl} {p:<14s} AUC {a:.3f}")
    print("  ...")
    for rank, (p, a) in enumerate(ranked[-3:], len(ranked) - 2):
        gl = "*" if all(c in GLASSES for c in p.split("+")) else " "
        print(f"  {rank:>2d}. {gl} {p:<14s} AUC {a:.3f}")

    best_glasses = [(p, a) for p, a in ranked
                    if all(c in GLASSES for c in p.split("+"))]
    if best_glasses:
        p, a = best_glasses[0]
        rank = [x[0] for x in ranked].index(p) + 1
        print(f"\n  Best glasses-reachable pair: {p} at AUC {a:.3f} "
              f"(rank {rank} of {len(ranked)})")

    out = os.path.join(os.path.dirname(DATA), "..", "results")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "surprise_channels.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  saved -> results/surprise_channels.json")


if __name__ == "__main__":
    main()
