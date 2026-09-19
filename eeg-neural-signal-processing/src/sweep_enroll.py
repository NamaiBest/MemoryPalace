"""Enrollment-size sweep, averaged over seeds.

A single random draw is noisy here because WHICH recordings you enroll on matters
as much as how many: enrolling only on eyes-closed then testing elsewhere is much
worse than a mixed enrollment. Averaging over seeds separates quantity from luck.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_auditory as LA, experiments as EX

d = LA.build(epoch_s=4.0)
cond, rec, subj = d["condition"].astype(str), d["recording"].astype(str), d["subject"]
rest = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
aud = ~rest
out = []
for n_rec in [1, 2, 3, 4, 5, 6]:
    accs, eers = [], []
    for seed in range(8):
        rng = np.random.RandomState(seed)
        tr = np.zeros(len(subj), bool)
        for s in np.unique(subj):
            rs = np.unique(rec[rest & (subj == s)])
            tr |= np.isin(rec, rng.choice(rs, size=min(n_rec, len(rs)), replace=False))
        r = EX.run_split(d, tr, aud, "x")
        accs.append(r["rank1_acc"]); eers.append(r["verification_eer"])
    rec_out = {
        "n_enroll_recordings": n_rec,
        "enroll_seconds_per_subject": n_rec * 120,
        "rank1_mean": float(np.mean(accs)), "rank1_std": float(np.std(accs)),
        "eer_mean": float(np.mean(eers)), "eer_std": float(np.std(eers)),
    }
    out.append(rec_out)
    print(f"enroll={n_rec} rec ({n_rec*120:>3d}s/subj)  "
          f"rank1={np.mean(accs)*100:5.2f}% +/-{np.std(accs)*100:4.2f}  "
          f"EER={np.mean(eers)*100:5.2f}% +/-{np.std(eers)*100:4.2f}", flush=True)

json.dump(out, open("/Users/namai/Documents/Project/HackMIT/results/enroll_sweep.json", "w"), indent=2)
print("\nsaved -> results/enroll_sweep.json")
