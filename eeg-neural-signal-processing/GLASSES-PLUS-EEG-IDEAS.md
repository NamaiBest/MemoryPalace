# Glasses + EEG - What This Setup Can Actually Do

Your idea: the glasses frame acts as the mechanical clamp, the EEG electrodes ride on it,
and a neural event triggers an action.

**The mechanical intuition is right. The device choice is wrong.** Below: why, what to
build instead, and nine other things this platform is good for.

---

## Part 1 - Reality check on the Ray-Bans

### You cannot put electrodes on a Meta Ray-Ban

HackMIT stocks Meta Ray-Ban Gen 1 and Gen 2, and Ray-Ban Display with the Neural Band.
They are useful, but not for what you described:

- **Sealed, non-modifiable hardware.** These are consumer devices on loan. You are not
  drilling electrode contacts into the temples.
- **No code runs on the glasses.** The Meta Wearables Device Access Toolkit (developer
  preview since December 2025, opened more broadly in 2026) works by letting you extend
  an existing **iOS or Android app**. Your code runs on the phone; the glasses are a
  camera and a speaker at the end of a Bluetooth link.
- **What you do get:** the 12 MP ultra-wide camera, the 5-mic array, and the open-ear
  speakers. That is a genuinely good capture and audio-feedback device.
- **What you do not get:** publishing through a storefront (still not open), and - the
  important one - **any access to raw sEMG from the Neural Band.** Meta exposes
  pre-processed gestures through proprietary algorithms; the raw voltages are behind a
  black box. The Neural Band cannot be repurposed as a general biosignal sensor.

**Consequence for your idea:** the Neural Band is not "an EEG-like sensor you can trigger
on." It is a gesture pad that emits a handful of recognized gestures. If a pinch gesture
is a good enough trigger, it is excellent and free. If you need a physiological signal,
it gives you nothing.

### The thing on the hardware list that actually solves this

> **"Non-prescription eyeglass frames used as wearable-prototype platforms"**

HackMIT explicitly stocks blank frames *for this purpose*. That is your answer. Build
your own instrumented frame; use the Ray-Bans, if at all, as a separate camera you talk
to over the phone.

---

## Part 2 - What a glasses frame can and cannot sense

A frame touches the head at exactly three places, and they are better sites than you
might expect:

| Contact point | 10-20 position | What you get |
|---|---|---|
| **Nose bridge / brow** | near Fp1, Fp2, nasion | Eye blinks and eye movement (EOG) - hundreds of µV, the largest signals on the head. Frontal theta and alpha. |
| **Temples** | near F7/F8, T7/T8 | Temporalis muscle (jaw clench) - very large. Frontal-temporal EEG. |
| **Behind the ears** | mastoid, M1/M2 | **The standard reference site.** This is the one that makes the whole thing electrically viable. |

That is a real montage. Note that the PhysioNet auditory EEG-biometric dataset used
**T7, F8, Cz, P4** - and *two of its four channels are reachable from a frame.*

**What you cannot reach, and it matters:**
- **Pz / Cz** - where P300 is largest. No P300 from glasses alone.
- **O1 / O2** - the cleanest alpha. You can still see frontal alpha, just weaker.
- **Motor cortex** - no motor imagery.

So: a glasses frame is an excellent **EOG + facial EMG + frontal EEG** device, and a poor
general-purpose EEG device. Design around that rather than against it.

This is now measured, not assumed. On the 4-channel auditory dataset the two
glasses-reachable positions (F8, T7) were the weakest pair in the montage - 47.68% rank-1
versus 54.89% for the two positions a frame cannot reach, and 70.65% for all four. The
same ordering reproduced on 109 subjects with 64 channels. Full tables in
[RESULTS.md](RESULTS.md).

### The mechanical problems, honestly

1. **Clamping force.** Frames are designed for comfort - roughly 1-3 N of temple
   pressure. Electrodes want firm, stable contact. Use spring-loaded pogo pins or
   conductive fabric pads at the temples, and a soft silver-cloth pad behind the ear.
   Do not just glue a flat disc on and hope.
2. **Weight and center of gravity.** Above about 30 g on the frame it becomes
   unpleasant fast, and anything front-heavy slides down the nose - which is also a
   motion artifact. Keep the board behind the ear or run a short tether to a
   neck-worn/pocket enclosure.
3. **Cable microphonics.** Moving wires generate voltage. Short leads, and secure
   everything. This is a bigger source of noise than you expect.
4. **Slippage is your enemy.** Every frame shift changes electrode position, which
   changes every feature you compute. A silicone nose pad and a thin retainer strap
   costs you nothing in looks and buys you a lot in signal.

### The realistic 36-hour build

Frame carries the electrodes and a reference behind the ear → short leads to an
**OpenBCI Ganglion** clipped to a collar or headband → BLE to a **Pi 5** or laptop. The
Ganglion is small but not glasses-small; do not try to mount the amp on the frame.

---

## Part 3 - Ten things to build with this

Ordered roughly by build feasibility. The first four are safe; the last few are ambitious.

### 1. EOG gesture control - the reliable version of "neural trigger"
Glasses sit right next to the eyes, which makes them a near-perfect
**electrooculography** device. A deliberate double-blink, or a look-left-look-right-
look-left sequence, produces an unambiguous 100+ µV pattern that is trivially separable
from noise.

**Why this matters:** you get a hands-free, silent, socially invisible trigger with a
near-zero false-positive rate. It is not "reading your mind," and you should not pitch it
as such - but as an *accessibility interface for someone who cannot reliably operate a
button*, it is genuinely valuable and it will work on stage every time.

### 2. Jaw-clench panic button
Temporalis EMG at the temples is enormous and detectable at ~90% accuracy on hardware as
crude as a single-channel NeuroSky. A deliberate double-clench commits the video buffer,
sends an alert, or calls a caregiver. Works with occupied hands, in the dark, without
speaking. For someone with tremor or limited hand mobility, this is a real improvement
over a wrist button.

### 3. Drowsiness and microsleep detection
Frontal theta rises, alpha rises, blinks lengthen and slow, and eye movements drift
before a microsleep. All of it is visible in exactly the montage a frame gives you, and
it is one of the best-validated results in applied EEG. Socially useful for
long-haul drivers, night-shift nurses, and machine operators - and it is a *continuous*
signal, so it demos well as a live gauge.

### 4. Wearer verification
A short enrollment at the start of the day, then a periodic 1:1 check that the frame is on
the person it was enrolled to. Same-session verification is the one regime where EEG
biometrics genuinely perform: **2.63% EER measured** on 109 subjects when enrolling
eyes-closed. Pitch it as a **privacy and correctness** feature - "this device will not log
a stranger, and it knows when it has been put on wrong" - not as security.

**Caveat measured on real data, and it is specific to this idea:** the electrode positions
a frame can reach are the *worst* ones for identity. On 109 subjects, a glasses-like
4-channel montage (Fp1, Fp2, T7, T8) scored 35.96% rank-1 / 18.35% EER against 82.26% /
7.61% for the full 64-channel cap - and it was beaten by the central montage a frame
cannot touch. See [RESULTS.md](RESULTS.md#8-consumer-hardware-costs-more-than-half-the-accuracy).
Budget a longer enrollment and a tolerant threshold, or pair EEG with a second modality.

### 5. Retrospective capture (your main idea, refined)
The rolling-buffer camera from [PLAN.md](PLAN.md#4--build-plan--retrospective-capture-the-one-to-build), 
with the frame supplying the trigger. The refinement that makes it work: **do not rely on
a subtle neural event.** Fuse a deliberate gesture (blink/clench) for user-initiated
capture with a passive multimodal score (frontal theta, heart rate from PPG, IMU
agitation) for automatic capture. Two paths to a commit, one of which always works.

### 6. Queryable memory - the feature that makes it a product
A buffer of clips is a filing cabinet nobody opens. Run a VLM over each committed clip,
store captions, and let the wearer ask *"where did I put my glasses case?"* or a caregiver
ask *"what happened before he got upset this afternoon?"* - answered by searching the
caption index, not by scrubbing video.

This is what SenseCam never had. The original research showed reviewing images restores
memory; it required a human to sit and page through thousands of them. Making the archive
*queryable in natural language* is the 2026 contribution, and it is the strongest single
idea in this document.

### 7. Absence-seizure and staring-spell logger
People with epilepsy dramatically underreport their own seizures - you cannot log an
event you were not conscious for, and absence seizures in particular are invisible to the
person having them. Generalized spike-wave is **frontally dominant**, so a frontal
montage can plausibly detect it, and the TUH TUEV corpus has the annotations to train on.

Pair it with the retrospective camera and you get an automatic seizure diary with video
context - which is exactly what a neurologist needs and almost never gets. Strong social
case, real unmet need, and there is annotated open data. **This is the most underrated
idea here.** Be careful to frame it as a logging aid, never as a diagnostic.

### 8. Sensory-overload early warning
For autistic wearers or people with migraine or PTSD, an approaching overload has
physiological precursors - frontal alpha asymmetry shifts, heart rate climbs, and the
environment itself is measurable (the mic array gives you sound pressure level; a light
sensor gives you brightness). The glasses can respond with their *own* affordance:
tint electrochromic lenses, switch the open-ear audio to noise masking, or quietly
suggest the nearest exit on the phone. The intervention lives on the same device as the
sensor, which is rare and elegant.

### 9. Caregiver handoff report
End of shift: N episodes, timestamped, each with a caption, a thumbnail, and the
physiological trace at the moment of the trigger. Care handoffs today are verbal and
lossy. This is unglamorous, requires no new sensing, and is probably the feature an
actual care facility would pay for. Build it - it is the slide that makes judges believe
you talked to a user.

### 10. Auditory attention decoding - the ambitious one
Which of two speakers is the wearer actually listening to? Decodable from EEG, and it is
the holy grail for hearing aids: steer the beamformer toward whoever the wearer is
attending to. The mic array is already on the glasses.

**Honest assessment:** hard with frontal-only channels, and normally done with far more
electrodes and longer integration windows. Do not attempt it in 36 hours. Worth knowing
it exists, because it is where this hardware category is heading.

---

## Part 4 - Combinations worth considering

- **Frame EEG + Ray-Ban camera.** Use the Ray-Bans via the Wearables Toolkit purely as
  the capture device, and your instrumented frame purely as the sensor. Two devices, but
  each does the thing it is actually good at. Requires the toolkit app working *before*
  the event.
- **Neural Band pinch as a manual trigger.** If you get Ray-Ban Display, the pinch
  gesture is a free, reliable, socially invisible commit button. No raw sEMG needed - just use the gesture Meta already exposes.
- **Frame EEG + MAX30102 PPG + BNO085 IMU.** All on HackMIT's list. Three independent
  modalities into one fusion score, so no single sensor failure kills your demo. This is
  the configuration I would actually build.
- **DRV2605L + LRA haptic in the temple.** A gentle buzz behind the ear as a
  reorientation cue - for a person with dementia who has stopped mid-task, or as
  confirmation that a trigger registered. Closes the loop, costs almost nothing, and
  makes the demo feel like a product rather than a script.
