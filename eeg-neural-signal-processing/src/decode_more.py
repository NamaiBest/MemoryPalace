"""Beyond a binary trigger: what else is in the signal?

Three families, each with the split that makes the answer honest:

  A. STATE      -- what is the wearer doing? (recording-level split, within subject)
  B. STIMULUS   -- what are they perceiving? (train in-ear, test bone-conduction, so
                   the model cannot cheat on the audio route)
  C. TRAITS     -- who are they? (leave-one-SUBJECT-out; the unit of analysis is the
                   subject, not the epoch, and n=20 means low power)
"""
import sys, os, json
import numpy as np
import pandas as pd
from scipy.stats import binomtest
sys.path.insert(0, os.path.dirname(__file__))
import load_auditory as LA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


def model():
    return make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))


NATIVE = {"inear_native_song", "bone_native_song"}
NONNAT = {"inear_nonnative_song", "bone_nonnative_song"}
INEAR = {"inear_native_song", "inear_nonnative_song", "inear_neutral_music"}
BONE = {"bone_native_song", "bone_nonnative_song", "bone_neutral_music"}

d = LA.build(epoch_s=4.0)
X, cond, rec, subj = d["X"], d["condition"].astype(str), d["recording"].astype(str), d["subject"]
out = {}

print("=" * 100)
print("A.  STATE decoding -- what is the wearer doing right now?")
print("=" * 100)

# A1: 3-way rest-open / rest-closed / listening, within subject, recording-level split
lab = np.where(cond == "rest_eyes_open", 0, np.where(cond == "rest_eyes_closed", 1, 2))
s3 = np.array([r.endswith("_s03") for r in rec])
# hold out session 3 for rest; hold out bone-conduction recordings for listening
te_mask = (s3 & (lab < 2)) | (np.isin(cond, list(BONE)))
accs = []
for s in np.unique(subj):
    tr = (subj == s) & ~te_mask
    te = (subj == s) & te_mask
    if len(np.unique(lab[tr])) < 3 or te.sum() == 0:
        continue
    m = model().fit(X[tr], lab[tr])
    accs.append((m.predict(X[te]) == lab[te]).mean())
print(f"  A1  3-way (rest-open / rest-closed / listening), within-subject : "
      f"{np.mean(accs)*100:5.2f}% +/-{np.std(accs)*100:4.2f}   chance=33.3%")
out["A1_3way_state_within"] = {"acc": float(np.mean(accs)), "std": float(np.std(accs)), "chance": 1/3}

# A2: same, cross-subject (zero calibration)
accs = []
for s in np.unique(subj):
    tr, te = subj != s, subj == s
    m = model().fit(X[tr], lab[tr])
    accs.append((m.predict(X[te]) == lab[te]).mean())
print(f"  A2  same, LEAVE-ONE-SUBJECT-OUT (no calibration)               : "
      f"{np.mean(accs)*100:5.2f}% +/-{np.std(accs)*100:4.2f}   chance=33.3%")
out["A2_3way_state_loso"] = {"acc": float(np.mean(accs)), "std": float(np.std(accs)), "chance": 1/3}

print()
print("=" * 100)
print("B.  STIMULUS decoding -- what are they perceiving?")
print("=" * 100)

# B1: native vs non-native language song. Train on IN-EAR, test on BONE-CONDUCTION,
# so the model cannot win by recognising the delivery route.
m_lang = np.isin(cond, list(NATIVE | NONNAT))
y_lang = np.isin(cond, list(NATIVE)).astype(int)
tr_route = np.isin(cond, list(INEAR))
accs = []
for s in np.unique(subj):
    tr = m_lang & (subj == s) & tr_route
    te = m_lang & (subj == s) & ~tr_route
    if len(np.unique(y_lang[tr])) < 2 or te.sum() == 0:
        continue
    m = model().fit(X[tr], y_lang[tr])
    accs.append((m.predict(X[te]) == y_lang[te]).mean())
print(f"  B1  native vs non-native song (train in-ear -> test bone)      : "
      f"{np.mean(accs)*100:5.2f}% +/-{np.std(accs)*100:4.2f}   chance=50.0%")
out["B1_language_crossroute"] = {"acc": float(np.mean(accs)), "std": float(np.std(accs)), "chance": 0.5}

# B2: in-ear vs bone conduction (a physical difference -- should be easier)
m_route = np.isin(cond, list(INEAR | BONE))
y_route = np.isin(cond, list(INEAR)).astype(int)
accs = []
for s in np.unique(subj):
    idx = m_route & (subj == s)
    recs = np.unique(rec[idx])
    te_r = [r for r in recs if "neutral" in LA.CONDITIONS.get(r.split("_")[1], "")]
    te = idx & np.isin(rec, te_r); tr = idx & ~np.isin(rec, te_r)
    if te.sum() == 0 or len(np.unique(y_route[tr])) < 2 or len(np.unique(y_route[te])) < 2:
        continue
    m = model().fit(X[tr], y_route[tr])
    accs.append((m.predict(X[te]) == y_route[te]).mean())
print(f"  B2  in-ear vs bone conduction (train songs -> test neutral)    : "
      f"{np.mean(accs)*100:5.2f}% +/-{np.std(accs)*100:4.2f}   chance=50.0%")
out["B2_route_crossstim"] = {"acc": float(np.mean(accs)), "std": float(np.std(accs)), "chance": 0.5}

print()
print("=" * 100)
print("C.  TRAIT decoding -- leave-one-SUBJECT-out. n=20, so power is low.")
print("    Unit of analysis is the SUBJECT (majority vote over their epochs), not the epoch.")
print("=" * 100)
meta = pd.read_csv("/Users/namai/Documents/Project/HackMIT/data/auditory/Subjects.csv")
meta.columns = [c.strip() for c in meta.columns]
meta["sid"] = meta["Subject ID"].str.extract(r"(\d+)").astype(int)
meta = meta.set_index("sid")

targets = {
    "mother language (Italian vs Arabic)": (
        lambda r: 1 if str(r["Mother Language"]).strip() == "Italian"
        else (0 if str(r["Mother Language"]).strip() == "Arabic" else None)),
    "age (above/below median 26)": (
        lambda r: 1 if r["Age"] > 26 else (0 if r["Age"] < 26 else None)),
    "BMI (above/below median)": (
        lambda r: 1 if r["BMI"] > 23.07 else 0),
}
for name, fn in targets.items():
    lut = {s: fn(meta.loc[s]) for s in meta.index if fn(meta.loc[s]) is not None}
    keep = np.isin(subj, list(lut))
    yy = np.array([lut.get(s, -1) for s in subj])
    subs = sorted(lut)
    correct = 0
    for s in subs:
        tr = keep & (subj != s); te = keep & (subj == s)
        if len(np.unique(yy[tr])) < 2:
            continue
        m = model().fit(X[tr], yy[tr])
        vote = int(np.round(m.predict(X[te]).mean()))   # majority vote for this subject
        correct += int(vote == lut[s])
    n = len(subs)
    p = binomtest(correct, n, 0.5).pvalue
    star = "significant" if p < 0.05 else "NOT significant"
    print(f"  {name:<38s}: {correct}/{n} subjects = {correct/n*100:5.1f}%  "
          f"(binomial p={p:.3f}, {star})")
    out[f"C_{name}"] = {"correct": correct, "n": n, "acc": correct / n, "p": float(p)}
print("=" * 100)
json.dump(out, open("/Users/namai/Documents/Project/HackMIT/results/decode_more.json", "w"), indent=2)
print("\nsaved -> results/decode_more.json")
