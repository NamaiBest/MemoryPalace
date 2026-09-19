"""3-class mental-imagery classification on aryan2's own EmotivPRO recordings.

Task: apple vs mouse vs remote. Each 10 s file is one trial of one class - the
intervalMarker.csv files are all empty, so the label lives at the FILE level only.
192 trials: 61 apple, 60 mouse, 71 remote. EPOC X, 14 channels, 128 Hz.

Evaluation is GROUPED by trial (file). Each 10 s trial is cut into 2 s epochs to get
more training examples, but a trial's epochs NEVER split across train/test - the
lesson from every other experiment in this repo is that epoch-level leakage inflates
accuracy, sometimes by double digits.
"""
import glob, os, csv, sys, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "eeg-neural-signal-processing", "src"))
import features as F

FS = 128.0
CH = ["AF3","F7","F3","FC5","T7","P7","O1","O2","P8","T8","FC6","F4","F8","AF4"]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(REPO, "dataset", "epocx-imagery", "extracted")


def load_trial(path):
    """Some exports have a metadata preamble line before the real header
    ('title:..., start timestamp:..., headset type:...') - skip it if present."""
    with open(path) as fh:
        rows = list(csv.reader(fh))
    start = 1 if rows[0] and rows[0][0].startswith("title:") else 0
    hdr = rows[start]
    idx = [hdr.index(f"EEG.{c}") for c in CH]
    rows = rows[start:]
    data = np.array([[float(r[i]) for i in idx] for r in rows[1:] if r[idx[0]] != ""],
                    dtype=np.float64)  # rows[1:] skips whichever row was the header
    return data.T  # (channels, samples)


def main():
    files = []
    for cls in ("apple", "mouse", "remote"):
        for p in sorted(glob.glob(f"{ROOT}/*/{cls}*bp.csv")):
            if "intervalMarker" not in p:
                files.append((p, cls))
    print(f"trials found: {len(files)} "
          f"({sum(c=='apple' for _,c in files)} apple, "
          f"{sum(c=='mouse' for _,c in files)} mouse, "
          f"{sum(c=='remote' for _,c in files)} remote)")

    X, y, groups = [], [], []
    bad = 0
    for gi, (path, cls) in enumerate(files):
        try:
            x = load_trial(path)
        except Exception:
            bad += 1
            continue
        if x.shape[1] < FS * 2:
            bad += 1
            continue
        for e in F.epoch_signal(x, FS, epoch_s=2.0, max_uv=None):
            X.append(F.epoch_features(e, FS))
            y.append(cls)
            groups.append(gi)
    X, y, groups = np.array(X), np.array(y), np.array(groups)
    print(f"epochs: {len(X)} from {len(set(groups))} trials ({bad} trials skipped)")
    print(f"amplitude sanity: p50={np.percentile(np.abs(X),50):.2f} "
          f"p99={np.percentile(np.abs(X),99):.2f}  any NaN: {np.isnan(X).any()}\n")

    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.pipeline import make_pipeline
    from sklearn.model_selection import GroupKFold

    le = LabelEncoder()
    yi = le.fit_transform(y)
    gkf = GroupKFold(n_splits=8)

    print("=" * 90)
    print(f"3-CLASS (apple/mouse/remote), GROUPED BY TRIAL, chance = 33.3%")
    print("=" * 90)
    accs = []
    all_true, all_pred = [], []
    for tr, te in gkf.split(X, yi, groups):
        if len(np.unique(yi[tr])) < 3:
            continue
        m = make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))
        m.fit(X[tr], yi[tr])
        pred = m.predict(X[te])
        accs.append(np.mean(pred == yi[te]))
        all_true.extend(yi[te]); all_pred.extend(pred)
    accs = np.array(accs)
    print(f"  GroupKFold(8): acc = {accs.mean()*100:.2f}% +/- {accs.std()*100:.2f}%  "
          f"(per-fold: {[f'{a*100:.1f}' for a in accs]})")

    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(all_true, all_pred)
    print(f"\n  confusion matrix (rows=true, cols=pred), order {list(le.classes_)}:")
    for i, row in enumerate(cm):
        print(f"    {le.classes_[i]:<8s} {row}")

    print()
    print("=" * 90)
    print("PAIRWISE (2-class), same grouping, chance = 50%")
    print("=" * 90)
    pair_results = {}
    for a, b in [("apple","mouse"),("apple","remote"),("mouse","remote")]:
        m2 = (y == a) | (y == b)
        Xp, yp, gp = X[m2], (y[m2] == a).astype(int), groups[m2]
        accs2 = []
        for tr, te in GroupKFold(n_splits=6).split(Xp, yp, gp):
            if len(np.unique(yp[tr])) < 2 or len(np.unique(yp[te])) < 2:
                continue
            m = make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))
            m.fit(Xp[tr], yp[tr])
            accs2.append(np.mean(m.predict(Xp[te]) == yp[te]))
        aa = np.array(accs2)
        pair_results[f"{a}_vs_{b}"] = {"mean": float(aa.mean()), "std": float(aa.std())}
        print(f"  {a:<8s} vs {b:<8s}: {aa.mean()*100:6.2f}% +/- {aa.std()*100:.2f}%")

    print()
    print("=" * 90)
    print("NEGATIVE CONTROL: shuffled labels (should collapse to chance)")
    print("=" * 90)
    rng = np.random.RandomState(0)
    y_shuf = rng.permutation(yi)
    accs_s = []
    for tr, te in gkf.split(X, y_shuf, groups):
        if len(np.unique(y_shuf[tr])) < 3:
            continue
        m = make_pipeline(StandardScaler(), LDA(solver="eigen", shrinkage="auto"))
        m.fit(X[tr], y_shuf[tr])
        accs_s.append(np.mean(m.predict(X[te]) == y_shuf[te]))
    accs_s = np.array(accs_s)
    print(f"  shuffled-label acc = {accs_s.mean()*100:.2f}% +/- {accs_s.std()*100:.2f}%  "
          f"(real result was {accs.mean()*100:.2f}%)")

    out = {
        "n_trials": len(files), "n_epochs": len(X),
        "three_class_acc_mean": float(accs.mean()), "three_class_acc_std": float(accs.std()),
        "confusion_matrix": cm.tolist(), "classes": list(le.classes_),
        "pairwise": pair_results,
        "shuffled_control_mean": float(accs_s.mean()),
    }
    outp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results.json")
    json.dump(out, open(outp, "w"), indent=2)
    print(f"\nsaved -> {outp}")


if __name__ == "__main__":
    main()
