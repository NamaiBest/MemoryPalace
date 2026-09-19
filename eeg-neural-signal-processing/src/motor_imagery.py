"""Volitional command: can the wearer *choose* to signal, by imagining a movement?

This is the biggest step past a trigger. A trigger is something the device notices.
Motor imagery is something the wearer DECIDES -- a hands-free, silent, socially
invisible command channel.

EEGMMIDB runs R04/R08/R12: imagine opening/closing the LEFT vs RIGHT fist.
Annotations: T1 = left fist, T2 = right fist.

Pipeline is the field-standard one for MI, not my generic band-power features:
CSP (Common Spatial Patterns) -> log-variance -> LDA. CSP learns spatial filters that
maximise variance ratio between classes, which is exactly what sensorimotor rhythm
lateralisation looks like.

Split is at the RUN level: train R04+R08, test R12.
"""
import sys, os, glob, json, warnings
import numpy as np
warnings.filterwarnings("ignore")
import mne
from mne.decoding import CSP
mne.set_log_level("ERROR")

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.pipeline import Pipeline

DATA = "/Users/namai/Documents/Project/HackMIT/data/eegmmidb"
# sensorimotor strip - where mu/beta desynchronisation lives
MOTOR = ["Fc3", "Fc1", "Fcz", "Fc2", "Fc4", "C5", "C3", "C1", "Cz", "C2", "C4", "C6",
         "Cp3", "Cp1", "Cpz", "Cp2", "Cp4"]
GLASSES = ["Fp1", "Fp2", "Af7", "Af8", "F7", "F8", "T7", "T8"]


def norm(c):
    return c.replace(".", "").strip().capitalize()


def load_runs(subj, runs, picks):
    """Return epochs (n_trials, n_ch, n_times) and labels for one subject."""
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
        raw.filter(7., 30., verbose=False)      # mu + beta, the MI band
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


def run(picks, label, n_comp=4):
    accs, ok_subs = [], []
    for s in range(1, 110):
        Xtr, ytr = load_runs(s, [4, 8], picks)
        Xte, yte = load_runs(s, [12], picks)
        if Xtr is None or Xte is None or len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
            continue
        try:
            clf = Pipeline([("csp", CSP(n_components=min(n_comp, len(picks)), log=True)),
                            ("lda", LDA(solver="eigen", shrinkage="auto"))])
            clf.fit(Xtr, ytr)
            a = clf.score(Xte, yte)
        except Exception:
            continue
        accs.append(a); ok_subs.append(s)
    accs = np.array(accs)
    # "BCI literacy" is conventionally accuracy >= 70% on a 2-class problem
    lit = float(np.mean(accs >= 0.70))
    print(f"  {label:<34s} n={len(accs):>3d} subj  mean={accs.mean()*100:5.2f}% "
          f"+/-{accs.std()*100:4.2f}  median={np.median(accs)*100:5.2f}%  "
          f">=70%: {lit*100:4.1f}% of people  best={accs.max()*100:5.1f}%")
    return {"label": label, "n_subjects": len(accs), "mean": float(accs.mean()),
            "std": float(accs.std()), "median": float(np.median(accs)),
            "frac_above_70": lit, "max": float(accs.max()),
            "accs": accs.tolist(), "subjects": ok_subs}


if __name__ == "__main__":
    print("=" * 104)
    print("MOTOR IMAGERY: imagined LEFT vs RIGHT fist. Train R04+R08 -> test R12. Chance = 50%.")
    print("=" * 104)
    out = [run(MOTOR, "17-ch sensorimotor strip"),
           run(GLASSES, "8-ch glasses-reachable (frontal/temporal)")]
    print("=" * 104)
    json.dump(out, open("/Users/namai/Documents/Project/HackMIT/results/motor_imagery.json", "w"), indent=2)
    print("\nsaved -> results/motor_imagery.json")
