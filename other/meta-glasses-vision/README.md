# Meta Glasses Vision App - Feasibility

## The question

Can we build and test an app for Meta's Ray-Ban glasses before HackMIT, without owning
the hardware, and is "editing the firmware" even the right way to think about it?

## Short answer

**No, you cannot edit the firmware, and you do not need to.** Meta's glasses run closed
firmware you cannot modify or replace. What you actually build is a normal Android
(Kotlin) or iOS (Swift) phone app using Meta's official **Wearables Device Access
Toolkit (DAT)**, and Meta provides a **Mock Device Kit** that simulates the glasses'
camera and audio so you can build and test most of this before ever touching real
hardware. This is genuinely good news for your plan.

## How it actually works (the architecture)

Your app does **not** run on the glasses. It runs on the phone. The real chain is:

```
Your Android/iOS app  <-->  Meta AI companion app  <-->  Bluetooth  <-->  the glasses
```

The Meta AI app is a required middleman - it owns the Bluetooth pairing and permission
handshake. Your app talks to the DAT SDK, which talks to the Meta AI app, which talks to
the glasses. You never get a socket directly to the glasses, and you never install
anything onto the glasses themselves. Sources:
[Meta's own toolkit announcement](https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/),
[developer FAQ](https://developers.meta.com/wearables/faq/).

## What the toolkit actually exposes

| Capability | Available via DAT SDK? |
|---|---|
| 12MP camera (photo + video streaming) | Yes - the headline feature |
| 5-mic array + open-ear speaker audio | Yes |
| Display (600x600px HUD, Ray-Ban Display model only) | Yes, added later than camera/audio |
| Neural Band gesture input (sEMG - wrist-worn, reads motor-nerve signals for finger/hand gestures) | Yes, Display model only |
| Raw IMU / accelerometer / gyroscope | **Not clearly exposed in the native DAT SDK.** A separate "Web Apps" surface is documented as getting motion/orientation + phone GPS, but that is a different, lighter-weight app model than the native Kotlin/Swift SDK - confirm current scope before relying on it. |
| Eye tracking | **Not available on any Ray-Ban model.** That sensor exists only on Meta's research-only Project Aria glasses, which are not available to hackathon teams. |

Full API reference:
[wearables.developer.meta.com/docs/reference/android/dat](https://wearables.developer.meta.com/docs/reference/android/dat/0.3).
Official SDK source:
[github.com/facebook/meta-wearables-dat-android](https://github.com/facebook/meta-wearables-dat-android) and the
[iOS equivalent](https://github.com/facebook/meta-wearables-dat-ios).

## Developing without the hardware

This is the part that matters most for a pre-HackMIT build: **Meta's Mock Device Kit**
simulates the entire SDK stack - app connection, permission requests, and sensor data -
so your app code runs identically against a mock device or a real one. Confirmed:

- **Camera + audio (the Gen 1/2 AI Glasses feature set): fully mockable.** Build and test
  this now, on a laptop, with zero hardware.
- **Display + Neural Band gesture input (the Display model): not yet supported by Mock
  Device Kit.** If your idea depends on the screen or on gesture input, you will need
  real hardware time at HackMIT itself to validate that part - budget for it, don't
  assume it "just works" on demo day.

Toolchain: **Android Studio Flamingo or newer**, Kotlin. Setup docs:
[wearables.developer.meta.com/docs/develop/dat/getting-started-toolkit](https://wearables.developer.meta.com/docs/develop/dat/getting-started-toolkit/).

**Practical recommendation:** start now with the camera+audio path in Mock Device Kit.
It is the one piece of this whole idea you can fully de-risk before the event.

## Your pivot ideas, evaluated against what's actually exposed

You raised three directions if the EEG angle doesn't pan out: a "GitHub for vision" with
crash/fall detection, and task automation via a repeated gesture (you said "double eye
tap"). Here's what's real:

**Fall / crash detection - buildable, and does not need EEG at all**, exactly as you
guessed. Two independent paths, and you can combine them:
1. **Computer vision on the camera feed**, processed on the phone: sudden orientation
   change, motion blur spike, or a scene-cut-like frame discontinuity all correlate with
   a fall or crash. This runs entirely on the Mock Device Kit's simulated camera feed
   today - no hardware needed to prototype the CV logic.
2. **The phone's own accelerometer/gyroscope.** Since the phone is a required part of
   the architecture anyway (see above), its motion sensors are trivially available in
   any Android app, with no DAT SDK dependency at all, and no mocking limitation.
   Combining phone IMU with glasses camera context is the more robust design, and it
   sidesteps the "is IMU actually exposed via DAT" uncertainty entirely.

Worth noting: your team's own HackMIT Brainstorm doc already has a closely related idea
- "WiFi RSSI/CSI Gesture Classification," flagged there for elderly fall detection via
ambient WiFi signal disturbance, no wearable required at all. That is a genuine
alternative or complement worth a line in your pitch: camera+IMU catches it on the
person, WiFi CSI could catch it in a room even if the glasses are off.

**Task automation via a repeated gesture - real, but "eye tap" is the wrong modality.**
There is no eye-tracking or blink sensor available on Ray-Ban glasses through the
official toolkit. The gesture channel that **is** real and documented is the **Neural
Band**: sEMG at the wrist, reading motor-nerve signals for subtle finger/hand movements,
with no per-user calibration needed. A "pinch twice to repeat the last action" pattern
is buildable on the Display + Neural Band model today. It needs real hardware to
validate (Mock Device Kit doesn't cover it yet - see above), but it is a legitimate,
demoable command channel that does not require solving any of the hard EEG problems in
[eeg-neural-signal-processing/](../../eeg-neural-signal-processing/).

## Open questions to resolve before committing to this track

- Confirm current DAT SDK scope for IMU/motion data directly (the "Web Apps" vs. native
  SDK distinction above needs a fresh check against the latest docs before you build
  around it).
- Confirm whether your team will actually be issued a Display + Neural Band unit at
  HackMIT specifically, vs. only the non-display Gen 1/2 AI Glasses - this determines
  whether the gesture-automation idea is available to you at all.
- Decide whether this becomes its own HackMIT pitch, or folds in as "how the wearer
  interacts with" whichever primary project (MemoryPalace / the EEG trigger) the team
  commits to - it's a UI/sensing layer more than a standalone product idea.
