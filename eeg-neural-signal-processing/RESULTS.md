# Preliminary Results - EEG Biometrics on Real Data

Everything below was computed on this machine from public data. Code is in
[src/](src/), raw numbers in [results/](results/). Nothing here is copied from a paper.

**Method (identical throughout):** 4 s epochs → per-channel Welch PSD → 5 log absolute
band powers + 5 relative band powers + 95% spectral edge frequency + 3 Hjorth parameters
(14 features/channel) → standardize → shrinkage LDA. Deliberately a classical baseline,
not a deep net: on subject pools this small it is competitive, it trains in seconds, and
when it fails you can see why.

**Every split is at the recording level.** This matters more than the model - see §1.

---

## Datasets actually downloaded

| Dataset | Size on disk | Subjects | Channels | Rate | Notes |
|---|---|---|---|---|---|
| [PhysioNet Auditory EEG-Biometric](https://physionet.org/content/auditory-eeg/1.0.0/) | 476 MB, 240/240 files | 20 | 4 (P4, Cz, F8, T7) | 200 Hz | OpenBCI Ganglion, gold cups + Ten20. 8 conditions × 20 subjects. |
| [PhysioNet EEGMMIDB](https://www.physionet.org/content/eegmmidb/1.0.0/) | 278 MB, 218/218 files | 109 | 64 | 160 Hz | Baseline runs only: R01 eyes-open, R02 eyes-closed. |

**BED could not be downloaded.** Despite being on Zenodo it is `access_right: restricted`
and needs an access request routed to the authors. That is the *only* one of the three
with sessions a week apart, so the true cross-day number remains out of reach here. This
was an error in my earlier writeup and the docs are now corrected.

**Download note:** physionet.org served at ~70 KB/s and refused connections above ~8
concurrent workers. The S3 mirror `physionet-open.s3.amazonaws.com` served the identical
files at ~730 KB/s. Use the mirror.

---

## 1. The methodology result: how a random split lies to you

Epochs cut from the same recording are highly correlated. Split them randomly and pieces
of every test recording sit in the training set.

| Split | Rank-1 | EER |
|---|---|---|
| Random epoch-level split (**wrong**) | **82.59%** | **5.21%** |
| Recording-level split (correct) | 74.00% | 8.28% |

The wrong split buys you **+8.6 points of accuracy and a 37% lower EER for free**. Both
numbers are on the same data with the same model; the only difference is the split.

If you build this at HackMIT, split by recording. If you read a paper reporting 99% on 20
subjects and it does not say how it split, this is usually why.

---

## 2. Identification works - the signal is genuinely there

20 subjects, chance = 5%.

| Experiment | Rank-1 | Rank-5 | EER |
|---|---|---|---|
| Resting eyes-open, train sessions 1+2 → test session 3 | 80.92% | 96.59% | 5.94% |
| Resting eyes-closed, train sessions 1+2 → test session 3 | 75.67% | 95.67% | 6.76% |

16× chance from four dry-ish electrodes and a linear model. **Your uniqueness question is
answered affirmatively** - there is real, individually-discriminative structure in a
4-channel resting EEG.

Note the gap between rank-1 and rank-5: the system is much better at producing a correct
*shortlist* (96%) than a correct *answer* (81%). That shape matters - see §6.

---

## 3. Changing your mental state costs you more than anything else

Same day. Same electrodes. Same paste. The subject just does something different.

| Train → Test | Rank-1 | EER | vs. within-condition |
|---|---|---|---|
| Resting → Auditory stimuli | 70.65% | 8.25% | −10 pts |
| Auditory → Resting | 56.79% | 15.70% | −24 pts |
| **Eyes-open → Eyes-closed** | **55.33%** | **17.43%** | **−26 pts, EER ×2.9** |

**Closing your eyes nearly triples the error rate.** Nothing physical changed - not the
cap, not the gel, not the day.

This is the template-aging argument, demonstrated on real data, and it is *the*
finding here. Published work reports EER going from ~5% within-session to ~22%
across sessions. This dataset cannot test across days at all, and it still reproduces
most of that degradation from a state change alone. Electrode replacement on a
different day would come **on top of** this.

Anyone claiming a deployable EEG authentication system needs to answer this question,
and "we enrolled and tested in the same sitting" is not an answer.

---

## 4. How long must the user sit still?

Train on resting, test on auditory. Only the analysis window length changes.

| Epoch length | Rank-1 | EER |
|---|---|---|
| 1 s | 50.36% | 15.19% |
| 2 s | 59.06% | 12.12% |
| 4 s | 70.65% | 8.25% |
| 8 s | 77.73% | 6.15% |
| 16 s | 84.62% | 4.69% |

Monotone, no saturation by 16 s. **Accuracy is bought with the user's time.** A 1-second
"instant unlock" is not on the table; a 16-second verification is plausible. This is the
collectability problem in one table.

## 5. How much enrollment data?

Averaged over 8 random draws of which recordings to enroll on (±1 s.d.).

| Enrollment | Rank-1 | EER |
|---|---|---|
| 1 recording (120 s) | 53.85% ± 4.64 | 19.50% ± 2.11 |
| 2 recordings (240 s) | 62.50% ± 2.77 | 13.06% ± 0.95 |
| 3 recordings (360 s) | 67.24% ± 3.09 | 10.85% ± 1.60 |
| 4 recordings (480 s) | 68.60% ± 1.60 | 9.94% ± 0.78 |
| 5 recordings (600 s) | 70.17% ± 0.90 | 8.61% ± 0.37 |
| 6 recordings (720 s) | 70.65% ± 0.00 | 8.25% ± 0.00 |

Diminishing returns after ~4 recordings. Note the **variance at small enrollment**: with
one recording the spread is ±4.6 points, because *which* state you enroll in matters as
much as how much data you collect. Enroll across varied states, not more of one.

---

## 6. Channel ablation - bad news for the glasses idea

Train resting → test auditory, 20 subjects, varying which of the 4 electrodes are used.

| Channels | Rank-1 | EER |
|---|---|---|
| All 4 (P4, Cz, F8, T7) | 70.65% | 8.25% |
| **Glasses-reachable (F8, T7)** | **47.68%** | **15.73%** |
| Non-glasses (P4, Cz) | 54.89% | 13.37% |
| Single T7 | 31.49% | 22.22% |
| Single F8 | 31.46% | 22.17% |
| Single Cz | 40.26% | 20.98% |
| Single P4 | 38.20% | 20.53% |

**The two positions an eyeglass frame can reach are the weakest pair in the montage.**
F8+T7 lose 23 points against the full set and are 7 points worse than the central/parietal
pair - which is exactly the pair a frame cannot touch.

This does not kill glasses-mounted EEG. It kills glasses-mounted EEG *as an
authentication product*, which was already the recommendation. Frontal and temporal sites
remain excellent for what [GLASSES-PLUS-EEG-IDEAS.md](GLASSES-PLUS-EEG-IDEAS.md) actually
proposes: eye movement, blink, jaw clench, drowsiness, and frontal theta/alpha.

---

## 7. Scaling to 109 subjects (EEGMMIDB, 64 channels)

### The number that is too good to be true

| Split | Subjects | Rank-1 | EER |
|---|---|---|---|
| **R01 first half → R01 second half** (same 61 s recording) | 109 | **98.69%** | **0.36%** |
| R01 eyes-open → R02 eyes-closed (different recording) | 109 | 82.26% | 7.61% |

98.69% on 109 subjects at 0.36% EER looks like a solved problem. It is the same
recording, split down the middle. Move to a *different recording of the same person on
the same day* and EER goes up **21×**. This is §1's lesson again, at scale, and it is why
headline EEG-biometric numbers should always be read with "split how?" in mind.

### Enrollment state matters, and the asymmetry is actionable

| Train → Test | Rank-1 | EER |
|---|---|---|
| Eyes-open → Eyes-closed | 82.26% | 7.61% |
| **Eyes-closed → Eyes-open** | **88.62%** | **2.63%** |

Enrolling on eyes-closed and verifying on eyes-open is **~3× better** than the reverse.
The likely reason is that eyes-closed produces strong, stable alpha - the most heritable
and most individually distinctive component of resting EEG - so it yields a richer
template. **Practical takeaway: enroll with eyes closed.** That is a free improvement and
it costs the user nothing.

### Population size is not the bottleneck

Averaged over 12 random draws of subjects (±1 s.d.):

| Population | Rank-1 | EER | Chance |
|---|---|---|---|
| 5 | 88.33% ± 11.55 | 6.71% ± 7.56 | 20.00% |
| 10 | 83.22% ± 7.65 | 10.03% ± 7.20 | 10.00% |
| 20 | 84.67% ± 7.04 | 8.15% ± 4.55 | 5.00% |
| 40 | 85.50% ± 4.85 | 6.91% ± 2.48 | 2.50% |
| 60 | 84.52% ± 3.36 | 7.24% ± 1.84 | 1.67% |
| 80 | 83.51% ± 1.32 | 7.41% ± 1.30 | 1.25% |
| 109 | 82.26% | 7.61% | 0.92% |

Two things worth noticing.

**Accuracy is flat from 5 to 109 people** while chance falls from 20% to 0.92%. Holding
~83% while the task gets 20× harder is a real demonstration that the features encode the
*individual*, not just "these particular few people happen to differ." Uniqueness: confirmed
again, more strongly than in §2.

**The variance at small N is enormous** - ±11.6 points at N=5, ±7.7 at N=10, versus ±1.3
at N=80. A single lucky draw of 10 subjects gave 96.67% in my first un-averaged run.
This is the statistical reason to distrust small-cohort biometric claims in *either*
direction: at N=50, a spread of several points is normal, so a reported 100% is not
necessarily the method being extraordinary.

## 8. Consumer hardware costs more than half the accuracy

109 subjects, eyes-open → eyes-closed, varying which of the 64 electrodes are used.

| Channel set | Ch | Rank-1 | EER |
|---|---|---|---|
| All 64 | 64 | 82.26% | 7.61% |
| Consumer 8 (Fp1/2, F7/8, T7/8, O1/2) | 8 | 46.48% | 16.27% |
| Glasses-like 8 (AF7/8, Fp1/2, F7/8, T7/8) | 8 | 45.14% | 16.41% |
| Central 4 (Cz, Pz, C3, C4) | 4 | 42.45% | 15.73% |
| **Glasses-like 4 (Fp1, Fp2, T7, T8)** | 4 | **35.96%** | **18.35%** |
| Occipital 2 (O1, O2) | 2 | 22.02% | 25.15% |

Dropping from a 64-channel research cap to 8 consumer-reachable electrodes costs
**36 points of rank-1 accuracy and more than doubles EER**. The glasses-reachable
montage is the worst 8-channel option tested and, at 4 channels, is worse than the
central-4 set that a frame cannot reach.

This reproduces §6 on 5× the subjects with 16× the electrodes. It is a consistent,
robust finding, not an artifact of one small dataset.

---

## 9. What this means for the project

**Answering your original question directly: yes, neural signatures are individually
distinctive, and I can now show it rather than cite it.** 82% rank-1 across 109 people at
0.92% chance, from a linear model on band power. The signal is unambiguously there.

**And the recommendation to not build authentication for HackMIT is now supported by
your own data, not just by literature:**

| Requirement for a usable auth system | Best measured here | Verdict |
|---|---|---|
| EER competitive with fingerprint (~0.1%) | 2.63% best case, 7-17% realistic | **50-170× worse** |
| Survives a change in user state | EER ×2.9 from *closing the eyes* | **Fails** |
| Survives a new day / re-placed electrodes | **Not testable** - BED is restricted | **Unknown, and literature says ~22%** |
| Works on consumer hardware | −36 pts going 64→8 channels | **Fails** |
| Fast to collect | 16 s needed for the best numbers | **Poor** |

Every one of those was a prediction in [PLAN.md](PLAN.md). All of them held.

**What the data does support** - and this is the useful outcome - is exactly the
fold-in recommended in [README.md](README.md):

- **Rank-5 accuracy stays at 88-97% where rank-1 falls to 82%.** EEG is good at producing
  a shortlist and bad at picking a winner. That is a *filter*, not a *decider*.
- For **wearer verification** - one enrolled person, one short session, "is this still the
  right head?" - 2.63% EER (enrolling eyes-closed) is genuinely usable, and it is a
  privacy feature rather than a security claim.
- Enroll eyes-closed, use ≥4 recordings, use ≥8 s windows. All three are free.

**Still unresolved:** the true cross-day number. That needs BED, which is restricted.
Request access now - it is the one experiment that would change the conclusion, in
either direction.

---

## Reproducing

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy scikit-learn pandas mne
.venv/bin/python src/download.py auditory      # 476 MB via the S3 mirror
.venv/bin/python src/download.py eegmmidb      # 278 MB
.venv/bin/python src/load_auditory.py 4.0 data/aud_feat_4s.npz
.venv/bin/python src/experiments.py data/aud_feat_4s.npz results/auditory_4s.json
.venv/bin/python src/sweep.py                  # epoch length
.venv/bin/python src/sweep_enroll.py           # enrollment size, seed-averaged
.venv/bin/python src/load_mmidb.py all
.venv/bin/python src/experiments_mmidb.py data/mmidb_feat_all.npz
.venv/bin/python src/sweep_pop.py              # population size, seed-averaged
```

Runtime end to end: roughly 25 minutes, most of it download.

---

## 10. Idea #2 tested: EEG as a *trigger* rather than an identity

Your intuition was that a trigger needs far less from the EEG than authentication does.
**That is correct, and it is now measured.** The trigger problem is easier on four axes
at once:

| | Biometric (idea #1) | Trigger (idea #2) |
|---|---|---|
| Task | 109-way classification | binary |
| Population | 1:N across strangers | 1:1, this wearer |
| Time | must survive days/weeks | same session, calibrated today |
| Latency | must answer now | **a rolling buffer means it can take 30 s** |

That last row is the one that changes everything, and it falls out of your own
architecture rather than out of better signal processing.

**Proxy target:** eyes-open vs eyes-closed. Not distress - but a real, internally
generated state change with no external marker, so it tests the mechanism honestly.

### Per-window thresholding does not work

| Window | Accuracy | AUC | FPR at 95% sensitivity |
|---|---|---|---|
| 0.5 s | 77.98% | 0.859 | 41.99% |
| 1 s | 79.80% | 0.878 | 36.42% |
| 2 s | 81.70% | 0.888 | 33.54% |
| 4 s | 84.17% | 0.915 | 25.44% |

AUC of 0.915 looks strong and is completely misleading for this application. A trigger is
evaluated *continuously* - at 4 s windows that is 900 decisions per hour - so a 25% FPR
means the thing fires constantly. **Good AUC is not a usable trigger.** This is the single
most common way a demo like this dies at 3 a.m.

### Requiring k consecutive windows fixes it

A real state change persists; noise does not. Event-level, within-subject:

| k | Threshold | Detection rate | False clips/hour | Latency |
|---|---|---|---|---|
| 1 | 0.90 | 100.0% | 19.5 | 5.4 s |
| 2 | 0.90 | 100.0% | 12.0 | 12.4 s |
| 3 | 0.90 | 100.0% | **3.0** | 21.0 s |
| 4 | 0.90 | 100.0% | **1.5** | 27.6 s |
| 5 | 0.90 | 90.0% | **0.0** | 34.4 s |

**100% detection at 1.5 false clips per hour, with 27.6 s of latency.**

And the latency is free. With a 120 s rolling buffer, spending 27.6 s deciding still
captures **92 seconds before the event began**. The buffer absorbs the entire detection
delay - which is why this architecture works where a real-time detector would not.

### Four honest caveats

1. **Eyes-closed is a *sustained* state.** Persistence filtering works precisely because
   the state lasts tens of seconds. A brief transient - a startle, a 2-second lapse - would
   be *rejected* by a 5-window filter. This validates triggers on sustained states
   (agitation, distress, drowsiness, disengagement) and **not** on instantaneous spikes.
2. **Eyes-closed is not distress.** This proves the mechanism, not the application. The
   target state needs its own labelled data.
3. **Per-wearer calibration is required.** Zero-calibration cross-subject was much worse:
   69.77% ± 14.69 accuracy, AUC 0.811. Budget a short enrollment for each wearer.
4. **"0.0 false clips/hour" is 0 out of 20 recordings.** With n=20 the true rate could
   plausibly be several per hour. Read the k=4 row (1.5/hr), not the k=5 row.

### Channels - good news for the glasses, for once

| Channel set | Accuracy | AUC |
|---|---|---|
| All 4 (P4, Cz, F8, T7) | 84.17% | 0.915 |
| **Glasses pair (F8, T7)** | **80.35%** | **0.892** |
| Single F8 | 79.48% | 0.886 |
| Single T7 | 73.29% | 0.782 |

The glasses-reachable pair loses only ~4 points here, and a **single frontal electrode
(F8) retains AUC 0.886**. Compare §6, where the same pair lost 23 points on the biometric
task.

**This is the clearest signal in the whole study: the electrodes a frame can reach are
bad for identity and fine for state.** Idea #2 is the one the hardware actually supports.

---

## 11. Beyond a trigger: what else is actually in the signal?

Tested four families on the data already downloaded. The results sort into a clear
hierarchy, and the ordering is not the intuitive one.

### A. State - what the wearer is *doing*  ✅ works

3-way: resting eyes-open / resting eyes-closed / listening. Chance = 33.3%.

| | Accuracy |
|---|---|
| Within-subject (calibrated on the wearer) | **69.60% ± 13.03** |
| Leave-one-subject-out (zero calibration) | 54.00% ± 12.48 |

Works, and **calibration is worth ~16 points**. This extends §10 from a binary trigger to
a graded state estimate - you can output a continuous index rather than a yes/no.

### B. Stimulus - what the wearer is *perceiving*  ❌ chance

Trained on in-ear delivery, tested on bone conduction, so the model cannot cheat by
recognising the audio route.

| | Accuracy | Chance |
|---|---|---|
| Native vs non-native language song | **50.83% ± 19.24** | 50% |
| In-ear vs bone conduction | 54.49% ± 20.96 | 50% |

**Nothing.** Four channels of band power carry no usable information about *what* the
person is listening to - not even whether it is their own language, and not even whether
the sound is arriving through the ear or the skull. Note the ±19-21% spread: that is
noise, not a weak effect.

### C. Traits - who the wearer *is*  ⚠️ not demonstrable at n=20

Leave-one-subject-out, majority vote per subject. **The unit of analysis is the subject,
not the epoch** - epochs within a person are not independent, and using them as N is how
demographic-decoding papers get inflated results.

| Target | Correct | Accuracy | Binomial p |
|---|---|---|---|
| Mother language (Italian vs Arabic) | 12/16 | 75.0% | 0.077 - not significant |
| Age (above/below median 26) | 7/16 | 43.8% | 0.804 |
| BMI (above/below median) | 10/20 | 50.0% | 1.000 |

No significant trait decoding here. But note the language result at p=0.077 - suggestive,
underpowered, and pointing exactly at the privacy concern raised in
[PLAN.md](PLAN.md): **absence of evidence at n=20 is not evidence of absence.** Gender,
smoking and medication were 16-vs-4 splits and too imbalanced to test at all. Treat raw
EEG as health data regardless of what this table shows.

### D. Volitional command - what the wearer *chooses* to signal  ⚠️ works for ~1 in 3

The biggest step past a trigger: a trigger is something the device *notices*; motor
imagery is something the wearer *decides*. EEGMMIDB R04/R08/R12, imagined left vs right
fist, CSP → LDA, train on two runs, test on the third. 109 subjects, chance = 50%.

| Channel set | Mean | Median | Reach ≥70% | Best subject |
|---|---|---|---|---|
| 17-ch sensorimotor strip (C3/C4/Cz…) | **62.04% ± 17.43** | 60.00% | **31.2%** | 100.0% |
| 8-ch glasses-reachable (frontal/temporal) | 54.22% ± 11.76 | 53.33% | 10.1% | 93.3% |

Two things matter here.

**Only 31% of people clear the usability bar** (≥70% on a 2-class task) even with proper
motor-cortex electrodes. The ±17.4% spread is the well-known "BCI illiteracy"
phenomenon, reproduced: some subjects hit 100%, many sit at chance. A demo that works
for your teammate may fail on a judge. *Caveat: subjects had no training or feedback, and
real BCI users improve substantially with practice - so 62% is a floor, not a ceiling.
Also only 15 test trials per subject, so individual estimates are coarse.*

**Motor imagery is not available from a glasses frame.** 54.22% is chance. Sensorimotor
rhythms live over the motor strip, which no eyeglass frame touches. If you want a
volitional command channel on glasses, it has to come from somewhere else - see below.

### The ordering, and what it means

| Rank | Question | Result |
|---|---|---|
| 1 | What is your body doing? (blink, jaw, gaze) | trivial - 100s of µV |
| 2 | What state are you in? | **69.6% (3-way, chance 33%)** |
| 3 | What do you choose to command? | **62.0%, usable for ~31% of people** |
| 4 | Who are you? | 82.3% but collapses on state change (§3) |
| 5 | What are you perceiving? | **chance** |
| 6 | What are your traits? | not demonstrable at n=20 |

**Your state is easier to read than what you are listening to.** That inversion is the
single most useful thing to understand about this technology.

Scalp EEG gives you the brain's *system metrics* - load, arousal, engagement, mode - not
its *application data*. It is closer to reading CPU utilisation than to reading which
program is running. Design for that and the technology delivers; design against it and
nothing works.

**A bigger model does not change this.** EEGNet or a transformer would likely add a few
points to A and D, where signal exists. It cannot help B or C, because the information is
not present in four channels of scalp potential. More model does not create information.

### Not tested here, but worth knowing

- **SSVEP is the strongest option for a glasses build.** Flicker UI elements at different
  frequencies; the occipital response locks to whichever the wearer looks at. It is the
  most reliable BCI paradigm (routinely >90%, minimal training, works for nearly everyone - no illiteracy problem). **Ray-Ban Display has a screen**, which makes this the natural
  volitional command channel for that hardware. The catch: it needs occipital electrodes,
  which a frame cannot reach - so it needs a band around the back of the head, or an
  ear-hook extension.
- **Graded output beats binary.** Rather than fire/don't-fire, emit a continuous
  engagement or distress index and let it modulate behaviour - recording quality, alert
  threshold, haptic intensity. §10's persistence filter is a special case of this.
- **Fusion is where the wins are.** EEG as one vote alongside PPG (HR/HRV), IMU
  (agitation), and the mic (sound level) will beat any single modality - and it degrades
  gracefully when one sensor drops out, which matters at 3 a.m. in a demo hall.
- **Not real on scalp EEG:** imagined speech, reading specific thoughts or memories,
  reliable single-trial emotion classification. Do not put these on a slide.

---

## 12. The Neurosity Crown's exact 8 channels, tested with real labels (not estimated)

`confusion-detector/CHANNELS.md` estimated Crown performance using nearby substitute
electrodes, because the surprise dataset used there lacks Crown's exact channels
(F5, F6, C3, C4, CP3, CP4, PO3, PO4). EEGMMIDB's 64-channel montage contains all 8 of
those names exactly - no substitution. Two real tasks, 109 subjects, already downloaded.

### State (biometric identity as a stand-in for "how much signal is in this montage")

Same eyes-open -> eyes-closed protocol as §7-8, restricted to Crown's 8 channels.

| Montage | Rank-1 | EER | vs. full 64ch |
|---|---|---|---|
| **Crown-exact (8ch)** | **42.81%** | **15.95%** | -39.6 points |
| All 64 channels | 82.39% | 7.64% | ceiling |

Both are enormously above the 0.92% chance floor for 109 people. Crown's spread across
four cortical regions (frontal/central/centro-parietal/parieto-occipital) carries real,
usable signal - just less than a full lab cap, which is the expected trade for a device
you put on in ten seconds.

### Command (imagined left vs right fist, CSP+LDA, train R04+R08 -> test R12)

| Montage | Mean | Median | Reach >=70% |
|---|---|---|---|
| 17-ch sensorimotor strip (§11) | 62.04% | 60.00% | 31.2% |
| **Crown-exact (8ch)** | **61.52%** | **60.00%** | **27.5%** |
| 8-ch glasses-reachable (§11) | 54.22% | 53.33% | 10.1% |

**Crown essentially matches the dedicated 17-channel sensorimotor strip** (61.5% vs
62.0%, both far above the 54.2% glasses ceiling) despite having fewer channels and not
being optimised for motor cortex coverage. C3/C4 sit almost exactly over the hand motor
areas, which is doing the work here - this is not a coincidence, it is why Crown's
designers put electrodes there.

### What this means

Crown is not a full research montage, and does not claim to be. But on both tasks tested
here, it captures a large fraction of what a much bigger array gets, and on both tasks
it is clearly, substantially better than anything a glasses frame can reach. This is the
same conclusion as `confusion-detector/CHANNELS.md`, now confirmed on a second, real
(not estimated) dataset with real task labels.

Caveat: neither eyes-open/closed nor motor imagery is "confusion." No public dataset
combines Crown's exact channels with a confusion/surprise label - that gap is still
open, and closing it needs a real recording session, not another public dataset.

Reproducing: `.venv/bin/python src/crown_exact.py` (~5 min, uses already-downloaded
`data/eegmmidb`).
