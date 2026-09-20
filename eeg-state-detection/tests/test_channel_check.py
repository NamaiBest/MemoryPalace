import numpy as np
import pytest

from eeg_moments.channel_check import CHANNEL_SETS, aligned_epochs, fit_subset, fixed_scores, indices
from eeg_moments.shin import EEG_CHANNELS
from test_background import trial_block


def test_fixed_features_read_the_stated_channels_and_windows():
    epochs = np.zeros((3, 28, 220))
    pz, c3, c4 = (EEG_CHANNELS.index(c) for c in ("Pz", "C3", "C4"))
    epochs[0, pz, 20 + 60:20 + 120] = 2.0      # 0.3-0.6 s after onset at 200 Hz, 0.1 s pre-stimulus
    epochs[1, c4, 20 + 40:20 + 160] = 1.0      # 0.2-0.8 s
    epochs[2, c3, 20 + 40:20 + 160] = 1.0
    np.testing.assert_allclose(fixed_scores(epochs, "fixed_pz_p300"), [2.0, 0.0, 0.0])
    np.testing.assert_allclose(fixed_scores(epochs, "fixed_c4_minus_c3"), [0.0, 1.0, -1.0])
    with pytest.raises(ValueError, match="Unknown"):
        fixed_scores(epochs, "nope")
    assert indices(CHANNEL_SETS["midline"]) == [EEG_CHANNELS.index(c) for c in ("AFz", "Cz", "Pz", "POz")]


def test_subset_fit_uses_only_its_channels():
    blocks = [trial_block(i, c) for i, c in enumerate((2, 3, 2, 3))]
    X, y, groups = aligned_epochs(blocks)
    assert X.shape[1:] == (28, 220) and y.sum() == 24 and len(set(groups)) == 4
    search = fit_subset(X, y, groups, CHANNEL_SETS["c3c4"])
    assert search.best_estimator_.named_steps["scale"].n_features_in_ == 10
    scores = search.best_estimator_.decision_function(X[:, indices(CHANNEL_SETS["c3c4"]), :])
    assert len(scores) == len(y)
    # The synthetic deflection is on every channel, so the midline subset separates too.
    midline = fit_subset(X, y, groups, CHANNEL_SETS["midline"])
    assert midline.best_score_ > 0.5
