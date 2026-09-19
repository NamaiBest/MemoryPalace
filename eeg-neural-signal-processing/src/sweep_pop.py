"""Does identification degrade as the population grows? Averaged over subject draws.

A single random draw of N subjects is very noisy at small N -- one lucky draw of 10
mutually-distinct people looks like a breakthrough. Average over draws.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import experiments as EX

d = dict(np.load("/Users/namai/Documents/Project/HackMIT/data/mmidb_feat_all.npz", allow_pickle=True))
d["feature_names"] = d["feature_names"].astype(str)
subj, run = d["subject"], d["run"]
all_s = np.unique(subj)
out = []
for n in [5, 10, 20, 40, 60, 80, 109]:
    accs, eers = [], []
    n_draws = 12 if n < len(all_s) else 1
    for seed in range(n_draws):
        rng = np.random.RandomState(seed)
        pick = rng.choice(all_s, size=n, replace=False) if n < len(all_s) else all_s
        m = np.isin(subj, pick)
        r = EX.run_split(d, m & (run == 1), m & (run == 2), "x")
        accs.append(r["rank1_acc"]); eers.append(r["verification_eer"])
    rec = {"n_pop": n, "n_draws": n_draws,
           "rank1_mean": float(np.mean(accs)), "rank1_std": float(np.std(accs)),
           "eer_mean": float(np.mean(eers)), "eer_std": float(np.std(eers)),
           "chance": 1.0 / n}
    out.append(rec)
    print(f"N={n:>3d} ({n_draws:>2d} draws)  rank1={np.mean(accs)*100:6.2f}% +/-{np.std(accs)*100:4.2f}  "
          f"EER={np.mean(eers)*100:6.2f}% +/-{np.std(eers)*100:4.2f}  chance={100/n:5.2f}%", flush=True)

json.dump(out, open("/Users/namai/Documents/Project/HackMIT/results/pop_sweep.json", "w"), indent=2)
print("\nsaved -> results/pop_sweep.json")
