"""Biometric evaluation: identification accuracy, verification EER, open-set rejection.

The point of this module is to make it hard to report only the flattering number.
"""
import numpy as np
from sklearn.metrics import roc_curve


def eer_from_scores(genuine, impostor):
    """Equal Error Rate + threshold. Higher score = more likely genuine."""
    y = np.r_[np.ones(len(genuine)), np.zeros(len(impostor))]
    s = np.r_[genuine, impostor]
    fpr, tpr, thr = roc_curve(y, s)
    fnr = 1 - tpr
    i = np.nanargmin(np.abs(fnr - fpr))
    return (fpr[i] + fnr[i]) / 2, thr[i], fpr, fnr


def verification_scores(proba, y_true, classes):
    """Turn a classifier's per-class probabilities into genuine/impostor score sets.

    For each test epoch, the probability assigned to its true subject is a genuine
    score; the probabilities assigned to every other subject are impostor scores.
    This is the standard way to get a verification EER out of a closed-set model.
    """
    idx = {c: i for i, c in enumerate(classes)}
    gen, imp = [], []
    for p, yt in zip(proba, y_true):
        ti = idx[yt]
        gen.append(p[ti])
        imp.extend(np.delete(p, ti))
    return np.asarray(gen), np.asarray(imp)


def rank_n(proba, y_true, classes, n=5):
    """Rank-N identification: is the true subject in the top N candidates?"""
    order = np.argsort(-proba, axis=1)[:, :n]
    cls = np.asarray(classes)
    return float(np.mean([yt in cls[o] for o, yt in zip(order, y_true)]))


def summarize(name, y_true, y_pred, proba, classes):
    acc = float(np.mean(y_true == y_pred))
    gen, imp = verification_scores(proba, y_true, classes)
    eer, thr, _, _ = eer_from_scores(gen, imp)
    r5 = rank_n(proba, y_true, classes, 5)
    chance = 1.0 / len(classes)
    return {
        "experiment": name,
        "n_subjects": len(classes),
        "n_test_epochs": len(y_true),
        "rank1_acc": acc,
        "rank5_acc": r5,
        "chance": chance,
        "verification_eer": eer,
    }


def fmt(r):
    return (f"{r['experiment']:<46s} "
            f"subj={r['n_subjects']:>3d} "
            f"n={r['n_test_epochs']:>5d} "
            f"rank1={r['rank1_acc']*100:6.2f}% "
            f"rank5={r['rank5_acc']*100:6.2f}% "
            f"chance={r['chance']*100:5.2f}% "
            f"EER={r['verification_eer']*100:6.2f}%")
