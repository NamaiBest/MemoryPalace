"""Why per-window thresholding fails as a trigger, and what fixes it.

A trigger is evaluated CONTINUOUSLY. At 4 s windows that is 900 decisions/hour, so
even 1% FPR = 9 spurious clips/hour. T1 measured 25-55% FPR at 95% sensitivity.
Useless.

The standard fix: require k CONSECUTIVE windows over threshold. A real state change
persists; noise does not. If windows were independent, FPR falls as p^k -- in practice
less, because EEG noise is autocorrelated, which is exactly why this must be measured.

Event-level evaluation, which is what actually matters for the product:
  - true detection  = fired at least once during an eyes-CLOSED recording
  - false alarm     = fired during an eyes-OPEN recording (-> a wasted 2-min clip)
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import load_auditory as LA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_curve

EPOCH_S = 4.0


def model():
    return make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))


def consecutive_fire(mask, k):
    """Index of first run of k consecutive True, else None."""
    run = 0
    for i, v in enumerate(mask):
        run = run + 1 if v else 0
        if run >= k:
            return i
    return None


def main():
    d = LA.build(epoch_s=EPOCH_S)
    cond, rec, subj = d["condition"].astype(str), d["recording"].astype(str), d["subject"]
    X = d["X"]
    m = np.isin(cond, ["rest_eyes_open", "rest_eyes_closed"])
    y = (cond == "rest_eyes_closed").astype(int)
    s3 = np.array([r.endswith("_s03") for r in rec])

    # sensitivity at strict FPR targets (per-window), within subject
    print("=" * 104)
    print("T4  Per-window ROC at STRICT operating points (within-subject, 4 s windows)")
    print("=" * 104)
    for target in [0.10, 0.01, 0.001]:
        sens = []
        for s in np.unique(subj):
            tr, te = m & (subj == s) & ~s3, m & (subj == s) & s3
            if te.sum() == 0 or len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
                continue
            mo = model().fit(X[tr], y[tr])
            sc = mo.predict_proba(X[te])[:, 1]
            fpr, tpr, _ = roc_curve(y[te], sc)
            ok = fpr <= target
            sens.append(tpr[ok].max() if ok.any() else 0.0)
        print(f"  at FPR<={target*100:5.1f}%  ->  sensitivity = {np.mean(sens)*100:5.1f}%  "
              f"(~{target*900:.1f} false windows/hr before persistence filtering)")

    # persistence filter, event level
    print()
    print("=" * 104)
    print("T5  PERSISTENCE FILTER: require k consecutive windows (event-level, within-subject)")
    print("=" * 104)
    print(f"  {'k':>2s} {'thresh':>7s} {'detect rate':>12s} {'false alarms':>13s} "
          f"{'false clips/hr':>15s} {'latency':>9s}")
    out = []
    for k in [1, 2, 3, 4, 5]:
        for thr_q in [0.5, 0.7, 0.9]:
            det, fa, lat, n_open, n_closed = 0, 0, [], 0, 0
            for s in np.unique(subj):
                tr = m & (subj == s) & ~s3
                if len(np.unique(y[tr])) < 2:
                    continue
                mo = model().fit(X[tr], y[tr])
                for r in np.unique(rec[m & (subj == s) & s3]):
                    sel = rec == r
                    sc = mo.predict_proba(X[sel])[:, 1]
                    fired = consecutive_fire(sc > thr_q, k)
                    closed = y[sel][0] == 1
                    if closed:
                        n_closed += 1
                        if fired is not None:
                            det += 1; lat.append((fired + 1) * EPOCH_S)
                    else:
                        n_open += 1
                        if fired is not None:
                            fa += 1
            if n_closed == 0 or n_open == 0:
                continue
            dr = det / n_closed
            far = fa / n_open
            # each open recording is 120 s -> false alarms per hour of quiet wearing
            fph = far * (3600.0 / 120.0)
            L = f"{np.mean(lat):.1f}s" if lat else "-"
            print(f"  {k:>2d} {thr_q:>7.2f} {dr*100:>11.1f}% {far*100:>12.1f}% "
                  f"{fph:>15.1f} {L:>9s}")
            out.append({"k": k, "threshold": thr_q, "detect_rate": dr,
                        "false_alarm_rate": far, "false_clips_per_hour": fph,
                        "mean_latency_s": float(np.mean(lat)) if lat else None})
    print("=" * 104)
    json.dump(out, open("/Users/namai/Documents/Project/HackMIT/results/trigger_persist.json", "w"), indent=2)
    print("\nsaved -> results/trigger_persist.json")


if __name__ == "__main__":
    main()
