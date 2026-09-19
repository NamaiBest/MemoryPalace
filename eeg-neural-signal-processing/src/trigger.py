"""Idea #2: can a few channels of EEG gate a recording?

This is a fundamentally different problem from biometrics and should be much easier:
  - binary (event / not-event), not 109-way
  - 1:1 (this person, calibrated today), not 1:N across a population
  - same-session, so no template aging -- the failure mode that killed the biometric
  - a rolling buffer means DETECTION LATENCY DOESN'T MATTER; you may take seconds

Proxy target: eyes-open vs eyes-closed. It is not "distress", but it is a real, internally
generated state change with no external marker, so it tests the mechanism honestly.

The metric that matters for a product is not accuracy. It is: at a sensitivity high
enough to not miss events, how many spurious clips per hour do you get?
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_auditory as LA, features as F

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_curve, roc_auc_score


def model():
    return make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))


def operating_point(y, score, target_sens=0.95, epoch_s=4.0):
    """At >= target sensitivity, what FPR -- and what does that mean per hour?"""
    fpr, tpr, thr = roc_curve(y, score)
    ok = tpr >= target_sens
    if not ok.any():
        return None
    i = np.argmax(ok)
    windows_per_hour = 3600.0 / epoch_s
    # a trigger starts a ~2.5 min commit, so re-triggers inside that are absorbed
    raw = fpr[i] * windows_per_hour
    clips = min(raw, 3600.0 / 150.0)
    return {"sensitivity": float(tpr[i]), "fpr": float(fpr[i]),
            "false_clips_per_hour": float(clips)}


def chan_idx(fn, keep):
    return np.array([i for i, n in enumerate(fn) if n.split("_")[0] in keep])


def main():
    out = {}
    print("=" * 100)
    print("T1  WITHIN-SUBJECT state detection (calibrate on the wearer, cross-recording)")
    print("=" * 100)
    for es in [0.5, 1.0, 2.0, 4.0]:
        d = LA.build(epoch_s=es)
        cond, rec, subj = d["condition"].astype(str), d["recording"].astype(str), d["subject"]
        fn = d["feature_names"].astype(str)
        m = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
        y = (cond == "rest_eyes_closed").astype(int)
        s3 = np.array([r.endswith("_s03") for r in rec])
        accs, aucs, ops = [], [], []
        for s in np.unique(subj):
            tr = m & (subj == s) & ~s3
            te = m & (subj == s) & s3
            if len(np.unique(y[tr])) < 2 or te.sum() == 0:
                continue
            mo = model().fit(d["X"][tr], y[tr])
            sc = mo.predict_proba(d["X"][te])[:, 1]
            accs.append((mo.predict(d["X"][te]) == y[te]).mean())
            if len(np.unique(y[te])) > 1:
                aucs.append(roc_auc_score(y[te], sc))
                op = operating_point(y[te], sc, 0.95, es)
                if op: ops.append(op)
        fc = [o["false_clips_per_hour"] for o in ops]
        print(f"  window={es:>4.1f}s  acc={np.mean(accs)*100:5.2f}%  AUC={np.mean(aucs):.3f}  "
              f"@95% sens -> FPR={np.mean([o['fpr'] for o in ops])*100:5.2f}%  "
              f"~{np.median(fc):.1f} false clips/hr (median)")
        out[f"T1_within_{es}s"] = {"epoch_s": es, "acc": float(np.mean(accs)),
                                   "auc": float(np.mean(aucs)),
                                   "fpr_at_95sens": float(np.mean([o["fpr"] for o in ops])),
                                   "median_false_clips_per_hour": float(np.median(fc))}

    print()
    print("=" * 100)
    print("T2  CROSS-SUBJECT (zero calibration: train on others, deploy on a new person)")
    print("=" * 100)
    d = LA.build(epoch_s=4.0)
    cond, subj = d["condition"].astype(str), d["subject"]
    fn = d["feature_names"].astype(str)
    m = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
    y = (cond == "rest_eyes_closed").astype(int)
    accs, aucs, ops = [], [], []
    for s in np.unique(subj):
        tr = m & (subj != s); te = m & (subj == s)
        mo = model().fit(d["X"][tr], y[tr])
        sc = mo.predict_proba(d["X"][te])[:, 1]
        accs.append((mo.predict(d["X"][te]) == y[te]).mean())
        aucs.append(roc_auc_score(y[te], sc))
        op = operating_point(y[te], sc, 0.95, 4.0)
        if op: ops.append(op)
    fc = [o["false_clips_per_hour"] for o in ops]
    print(f"  leave-one-subject-out  acc={np.mean(accs)*100:5.2f}% +/-{np.std(accs)*100:4.2f}  "
          f"AUC={np.mean(aucs):.3f}  @95% sens -> FPR={np.mean([o['fpr'] for o in ops])*100:5.2f}%  "
          f"~{np.median(fc):.1f} false clips/hr")
    out["T2_cross_subject"] = {"acc": float(np.mean(accs)), "acc_std": float(np.std(accs)),
                               "auc": float(np.mean(aucs)),
                               "median_false_clips_per_hour": float(np.median(fc))}

    print()
    print("=" * 100)
    print("T3  CHANNEL COUNT (within-subject, 4 s) -- can a glasses frame do it?")
    print("=" * 100)
    rec = d["recording"].astype(str)
    s3 = np.array([r.endswith("_s03") for r in rec])
    for label, keep in {"all 4 (P4,Cz,F8,T7)": ["P4","Cz","F8","T7"],
                        "glasses pair (F8,T7)": ["F8","T7"],
                        "single T7": ["T7"], "single F8": ["F8"]}.items():
        ci = chan_idx(fn, keep)
        accs, aucs, ops = [], [], []
        for s in np.unique(subj):
            tr = m & (subj == s) & ~s3; te = m & (subj == s) & s3
            if te.sum() == 0 or len(np.unique(y[tr])) < 2: continue
            mo = model().fit(d["X"][tr][:, ci], y[tr])
            sc = mo.predict_proba(d["X"][te][:, ci])[:, 1]
            accs.append((mo.predict(d["X"][te][:, ci]) == y[te]).mean())
            if len(np.unique(y[te])) > 1:
                aucs.append(roc_auc_score(y[te], sc))
                op = operating_point(y[te], sc, 0.95, 4.0)
                if op: ops.append(op)
        fc = [o["false_clips_per_hour"] for o in ops]
        print(f"  {label:<24s} acc={np.mean(accs)*100:5.2f}%  AUC={np.mean(aucs):.3f}  "
              f"~{np.median(fc):.1f} false clips/hr")
        out[f"T3_{label}"] = {"acc": float(np.mean(accs)), "auc": float(np.mean(aucs)),
                              "median_false_clips_per_hour": float(np.median(fc))}
    print("=" * 100)
    os.makedirs("/Users/namai/Documents/Project/HackMIT/results", exist_ok=True)
    json.dump(out, open("/Users/namai/Documents/Project/HackMIT/results/trigger.json", "w"), indent=2)
    print("\nsaved -> results/trigger.json")


if __name__ == "__main__":
    main()
