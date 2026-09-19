"""How long a recording do you actually need? And how much enrollment data?

Both questions matter for a wearable: they set how long the user must sit still.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_auditory as LA, evaluation as EV, experiments as EX

results = {"epoch_len": [], "enroll": []}

# ---- epoch length sweep: train on resting, test on auditory (the honest split) ----
for es in [1.0, 2.0, 4.0, 8.0, 16.0]:
    d = LA.build(epoch_s=es)
    cond = d["condition"].astype(str)
    rest = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
    r = EX.run_split(d, rest, ~rest, f"epoch={es:g}s rest->auditory")
    r["epoch_s"] = es
    results["epoch_len"].append(r)
    print(EV.fmt(r), flush=True)

print("-" * 118, flush=True)

# ---- enrollment sweep: how many resting recordings per subject do you need? ----
d = LA.build(epoch_s=4.0)
cond, rec = d["condition"].astype(str), d["recording"].astype(str)
subj = d["subject"]
rest = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
aud = ~rest
rng = np.random.RandomState(0)
for n_rec in [1, 2, 3, 4, 6]:
    tr = np.zeros(len(subj), bool)
    for s in np.unique(subj):
        rs = np.unique(rec[rest & (subj == s)])
        pick = rng.choice(rs, size=min(n_rec, len(rs)), replace=False)
        tr |= np.isin(rec, pick)
    r = EX.run_split(d, tr, aud, f"enroll={n_rec} resting rec(s)/subj -> auditory")
    r["n_enroll_recordings"] = n_rec
    r["enroll_seconds_per_subject"] = n_rec * 120
    results["enroll"].append(r)
    print(EV.fmt(r), flush=True)

os.makedirs("/Users/namai/Documents/Project/HackMIT/results", exist_ok=True)
json.dump(results, open("/Users/namai/Documents/Project/HackMIT/results/sweeps.json", "w"), indent=2)
print("\nsaved -> results/sweeps.json")
