# MemoryPalace interpretation of the surprise-EEG experiment

## A. What we demonstrated

**EEG can detect this dataset’s experimentally defined surprise event**, at the
*epoch* level, above chance, in people the model has never seen.

Evidence:

- A surprise-related event-related response is visible in the grand average
  (Cz difference about +4.5 µV at 192 ms; posterior channels similar).
- Leave-one-subject-out random forest: balanced accuracy **0.65**, ROC-AUC
  **0.75** versus 0.50 chance.
- Shuffled-label and pre-event-only controls sit at chance.

**EEG cannot, in this setup, run as a clean continuous bookmark trigger.**
When we require several consecutive positive windows and a cooldown, and we
pick that rule on training subjects only, we either flood the log (~200 false
triggers/hour) or miss almost every event (~1.5% detection, still ~29 false
triggers/hour).

We did **not** demonstrate detection of insight, error awareness, or
spontaneous real-world aha.

---

## B. What that means for MemoryPalace

The result is **evidence for using EEG as one component** of a
cognitive-transition detector, and **evidence against shipping EEG-alone**
as the MemoryPalace trigger.

Practically:

- Keep a rolling audiovisual buffer. Latency of ~1 s is free if the buffer
  already holds the last two minutes.
- Do not promise “the glasses will know when you understand something”
  from two dry temples. F7/F8 LOSO AUC is ~0.60.
- A 4-channel OpenBCI-like montage (Fz, Cz, F7, F8) still carries some of
  the surprise-related response (AUC ~0.70). That is the honest hardware
  story if HackMIT hands you a Ganglion, not a 16-channel cap.
- The product claim should stay: *bookmark the context around a detected
  physiological transition*, with EEG as a vote, plus button / IMU / PPG /
  pupil when we have them.

This aligns with, rather than replaces, the teammate finding that a
*state-change* trigger can be made usable with persistence — their proxy
(eyes-open vs closed) is a large, lingering state. Surprise here is a brief
ERP. Persistence helps noise; it also waits out the event.

---

## C. What this does NOT demonstrate

- Universal cognitive-transition detection
- Memory decoding
- Thought decoding
- Spontaneous aha detection
- Clinical utility
- That a surprise ERP is the same as an insight / “I was wrong” / novelty
  experience in the wild
- That Meta Ray-Ban glasses can host F7/F8. They cannot. Blank frames can.

---

## D. What to run at HackMIT for actual insight

A **controlled insight / problem-solving task with participant self-report**,
not another surprise oddball.

Suggested 15-minute protocol:

1. Remote-associate or matchstick/anagram items on a laptop.
2. Participant hits a key (or jaw-clench, if EEG is noisy) at the moment they
   think they have it, then says **insight vs analysis** and **confidence**.
3. Record EEG (OpenBCI 4 or 8 ch), optional MAX30102 PPG, optional pupil from
   a webcam if quality allows.
4. Same pipeline as this folder: epoch around the *report*, LOSO if multiple
   teammates, otherwise within-person train/test by item. Report false
   bookmarks per hour on a later rest / scrolling-phone block.

Success for the hackathon is not “AUC 0.99 on aha.” It is: a buffer that
commits when a **conservative** fused score fires, plus an honest slide that
surprise-EEG worked as a timed proxy and insight is still a self-report
experiment.

---

## Continue with MemoryPalace?

**Yes**, as a multimodal, buffer-first product with EEG as supporting
evidence — not as a mind-reading sensor. This dataset de-risks the claim
“EEG changes at a labeled cognitive event” and re-risks the claim “that is
enough to auto-bookmark a day without spam.” The next sensor to add is
pupil/PPG, not more EEG channels the glasses cannot reach.
