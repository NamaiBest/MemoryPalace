"""Scale test on EEGMMIDB: 109 subjects, 64 channels, baseline runs only.

R01 = eyes open, R02 = eyes closed, one session each, same cap placement.
The R01->R02 split is a STATE change with placement held constant -- the same
comparison as E2c on the auditory set, but at 5x the subject count.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import evaluation as EV, experiments as EX

CONSUMER8 = ["Fp1", "Fp2", "F7", "F8", "T7", "T8", "O1", "O2"]
GLASSES = ["Af7", "Af8", "Fp1", "Fp2", "F7", "F8", "T7", "T8"]
GLASSES4 = ["Fp1", "Fp2", "T7", "T8"]
CENTRAL4 = ["Cz", "Pz", "C3", "C4"]


def chan_idx(fn, keep):
    return np.array([i for i, n in enumerate(fn) if n.split("_")[0] in keep])


def main(npz):
    d = dict(np.load(npz, allow_pickle=True))
    fn = d["feature_names"].astype(str)
    subj, run, eidx = d["subject"], d["run"], d["epoch_idx"]
    res = []
    n_subj_total = len(np.unique(subj))
    print(f"\nLoaded {d['X'].shape[0]} epochs, {d['X'].shape[1]} features, "
          f"{n_subj_total} subjects, {len(d['channels'])} channels\n")
    print("=" * 118)

    # ---- M1: within-run, temporally split (optimistic ceiling) ----
    half = np.median(eidx[run == 1])
    m_tr = (run == 1) & (eidx <= half)
    m_te = (run == 1) & (eidx > half)
    r = EX.run_split(d, m_tr, m_te, "M1 R01 first half -> R01 second half (same run)")
    if r: res.append(r); print(EV.fmt(r))

    # ---- M2: cross-run = state change, placement constant ----
    r = EX.run_split(d, run == 1, run == 2, "M2 R01 eyes-open -> R02 eyes-closed")
    if r: res.append(r); print(EV.fmt(r))
    r = EX.run_split(d, run == 2, run == 1, "M2b R02 eyes-closed -> R01 eyes-open")
    if r: res.append(r); print(EV.fmt(r))
    print("-" * 118)

    # ---- M3: how does it scale with population size? ----
    rng = np.random.RandomState(0)
    all_s = np.unique(subj)
    for n in [10, 20, 40, 60, 80, n_subj_total]:
        if n > len(all_s):
            continue
        pick = rng.choice(all_s, size=n, replace=False) if n < len(all_s) else all_s
        m = np.isin(subj, pick)
        r = EX.run_split(d, m & (run == 1), m & (run == 2), f"M3 N={n:>3d} subjects  R01->R02")
        if r: r["n_pop"] = int(n); res.append(r); print(EV.fmt(r))
    print("-" * 118)

    # ---- M4: channel sets, all 109 subjects, honest R01->R02 split ----
    sets = {
        "ALL 64 channels": list({n.split("_")[0] for n in fn}),
        "CONSUMER 8 (Fp,F7/8,T7/8,O1/2)": CONSUMER8,
        "GLASSES-LIKE 8 (AF,Fp,F7/8,T7/8)": GLASSES,
        "GLASSES-LIKE 4 (Fp1,Fp2,T7,T8)": GLASSES4,
        "CENTRAL 4 (Cz,Pz,C3,C4)": CENTRAL4,
        "OCCIPITAL 2 (O1,O2)": ["O1", "O2"],
    }
    for label, keep in sets.items():
        ci = chan_idx(fn, keep)
        if len(ci) == 0:
            continue
        r = EX.run_split(d, run == 1, run == 2, f"M4 [{label}]", chan_idx=ci)
        if r: r["n_channels"] = len(ci) // 14; res.append(r); print(EV.fmt(r))
    print("=" * 118)
    return res


if __name__ == "__main__":
    res = main(sys.argv[1])
    out = "/Users/namai/Documents/Project/HackMIT/results/mmidb.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), indent=2)
    print(f"\nsaved -> {out}")
