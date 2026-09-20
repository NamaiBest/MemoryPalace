# Smoothing the original VP002 band-power output

This is an exploratory follow-up on already inspected VP002, not fresh validation.
Its purpose is to isolate exponential smoothing using the exact saved task/rest
band-power classifiers from `outputs/workload_vp002`. No electrode changes, new
feature representation, classifier refitting for evaluation, or threshold tuning.

Use the same 28 EEG channels, preprocessing, two-second features, 0.25-second scan
grid, six calibration blocks and final three evaluation blocks per session. Restore
the original preprocessing identity and verify calibration sample hashes. Preserve
the original classifier weights, selected regularization, feature scaler and zero
decision boundary. Invalid windows remain NaN and reset smoothing. A nonnegative
score must persist for three seconds to create an interval, unchanged from before.

Select a smoothing half-life from 0.5, 1 and 2 seconds separately per session. To
avoid selecting from resubstitution scores, clone the saved classifier architecture
with its already-selected C and refit temporary classifiers within the original two
whole-block calibration folds. Fit on nonoverlapping labeled two-second windows;
score all valid centers in the opposite calibration blocks and smooth their margins.
Choose mean fold balanced accuracy at zero, then mean AUROC, then shorter half-life.
The original C was selected on these calibration blocks; these conditional CV scores
are model selection only, not an independent accuracy estimate. Temporary fold fits
never replace or alter the original saved classifier. Freeze all three half-lives
before accessing any evaluation scores in this run.

For evaluation, compute one margin sequence from each saved classifier. The two
alternatives are exactly that sequence and its exponentially smoothed version:
alpha = 1 - 2^(-0.25 / half_life). Initialize at the first usable margin of each
contiguous region; rejected centers end a region. Score classification on the same
nonoverlapping labeled centers and assess intervals on the same nine task blocks
and 72 seconds of labeled rest. Check identical masks, raw scores against the prior
reports (numerical tolerance 1e-12), and exact reproduction of the original 34 event
exports. Saved model bytes and in-memory fitted state must remain unchanged.

Report per-session and mean balanced accuracy/AUROC, sensitivity, specificity,
whole-task matches at IoU >=0.5, task coverage, rest included, interval count, and
matched-boundary errors. Descriptive improvement requires more whole-task matches,
no lower mean balanced accuracy, and no extra labeled rest overlap. Report tradeoffs
when this joint condition fails. No significance, generalization, spontaneous
cognitive-state or phone-video corroboration claims. All exports are replay EEG.
