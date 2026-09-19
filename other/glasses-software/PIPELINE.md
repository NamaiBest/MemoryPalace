# End-to-end pipeline: N400 semantic-difficulty → glasses recording

Scope, decided: **semantic difficulty only.** One signal, one sensor, one detector.
No startle detector, no IMU path, no separate microcontroller.

---

## 1. The architecture: the phone is the brain

```
   HEADSET (Neurosity Crown, or Emotiv Insight)
        |  Bluetooth LE
        v
   PHONE APP  <- the whole brain lives here
        |  1. BLE ingest, 256 Hz x 8ch
        |  2. filter -> features -> N400 detector
        |  3. spike fires -> SpikeEvent
        |  4. call Meta DAT SDK
        v
   META AI APP -> Bluetooth -> RAY-BAN GLASSES
        |
        v
   30 s recorded, forward from the trigger
```

**This works, and it is the right call.** No Pi, no ESP32, no firmware on the glasses.
The phone was already mandatory (the glasses are only reachable through the Meta AI
companion app), so putting the detector there removes a device rather than adding one.

One clarification on "connected to the Meta AI app": your app does not extend or modify
the Meta AI app. It is a **separate app you write** that uses the Wearables Device Access
Toolkit; the toolkit routes through the Meta AI app for pairing and permissions. You
never touch Meta's app itself, and you write no glasses firmware. Your instinct was
right, the plumbing is just slightly indirect.

---

## 2. Headset: Crown wins, and EPOC X is blocked for a reason that has nothing to do with bulk

You ruled out EPOC X for bulk. There is a harder blocker underneath that.

| Device | Channels | N400 coverage | Raw EEG on mobile | Verdict |
|---|---|---|---|---|
| **Neurosity Crown** | 8: CP3 C3 F5 PO3 PO4 F6 C4 **CP4** | **Good** - CP3/CP4/C3/C4 is real centro-parietal coverage, which is where N400 lives | **Free.** Official **BLE + React Native SDK**, `bluetooth-with-wifi-fallback` so it runs with no internet | **Use this** |
| **Emotiv Insight** | 5: AF3 AF4 T7 T8 **Pz** | **Pz is the single best N400 electrode.** Only 5 channels, 128 Hz | **Free** - Insight is a *consumer* device, all data streams included | Strong backup |
| Emotiv EPOC X | 14, all lateral | **Weak** - no midline, no CP. Its best parietal sites are P7/P8, off to the sides | **Paid.** EPOC X is a *professional* device: free tier gives Basic BCI only, **raw EEG needs a paid Developer API licence** | **Blocked** |

Three things worth pulling out:

- **EPOC X would have failed even if it were tiny.** Raw EEG on professional Emotiv
  hardware sits behind a paid licence. Do not discover this at the venue.
- **Insight is the cheap surprise.** Fewer channels than EPOC X, but it is a consumer
  device so raw access is free, it has BLE 5, and it has **Pz** - which EPOC X, with
  nearly three times the channels, does not.
- **Crown's BLE support is specifically React Native.** That is a mobile framework, so
  the phone-app plan has an officially supported path rather than a reverse-engineered
  one. Node.js BLE is not supported yet; Web and React Native are.

This reverses the "OpenBCI Cyton for trainability" call from the previous version. That
was right about training data and wrong about deployment: a headset you cannot wear or
stream from on a phone is worth less than public datasets are worth.

---

## 3. The honest problem with N400, and how to get around it

**N400 is normally an averaged measurement, not a single-event one.**

The most directly relevant study - a consumer 4-electrode Muse used to capture N400 -
found the effect reliably, but needed **24-27 trials to reach a dependability of 0.70**,
and analysed ~43 trials per condition. Single-trial N400 classification in the wider
literature runs above chance but modest, and is markedly better subject-dependent than
subject-independent.

So this does not work:

> one hard word → one clean N400 → one photo

Two things rescue it.

**(a) A real reading struggle is not one 400 ms blip.** When you hit a word you do not
know, you produce the N400 *and then* you dwell, re-read, and stay effortful for several
seconds. That trailing effort is exactly the sustained frontal theta that
`confusion-detector/` already detects at ~7 false alarms/hour. Using the transient and
the sustained feature together is still **one sensor and one detector** - it is the same
EEG stream, just fast and slow features. That is why `SpikeKind` keeps `LOAD` alongside
`SEMANTIC`.

**(b) Calibrate per wearer.** Subject-dependent models beat subject-independent ones
here, and `eeg-neural-signal-processing/RESULTS.md` §11 measured per-wearer calibration
worth ~16 points on a state task. A 3-4 minute calibration where the wearer reads
word pairs (some sensible, some nonsense) gives you their own N400 template. This is
exactly the ERP CORE N400 paradigm and is straightforward to script.

**What to promise:** not "it catches every word you did not know," but "it catches
moments you got stuck." Aim for recall over precision and let the 30-second clips be
cheap.

---

## 4. Training data

Deploying on Crown or Insight, but **no labelled dataset exists for either** (confirmed
for Crown twice, including reading its source code). So:

1. **[ERP CORE](https://osf.io/thsqg/)** (40 participants, CC BY-SA) contains the
   **N400** paradigm - word pairs, related vs unrelated - and is the single highest-value
   download. Research-grade hardware, so subset the channels toward whichever headset you
   pick, the way `confusion-detector/src/surprise_channels.py` already does.
2. **Record your own calibration set.** With no matching public data, ~30 minutes of the
   wearer doing the word-pair task on the actual headset is worth more than any public
   dataset recorded on other hardware. This also gives you the per-wearer template
   from §3(b).

`my-dataset/` (imagined apple/mouse/remote) does not apply here, as you said - voluntary
sustained imagery is different physiology from an involuntary semantic response.

---

## 5. What to build before HackMIT

1. **ERP CORE N400 detector, offline.** The science risk. If it does not work on clean
   research data it will not work on a dry headset at 3 a.m.
2. **React Native app: Crown BLE ingest.** Officially supported; get the stream landing
   on the phone with signal-quality readout.
3. **Kotlin/RN module for the DAT SDK, against Meta's Mock Device Kit** - simulates the
   whole glasses SDK with no hardware present. The platform risk, fully testable now.
4. **The word-pair calibration screen.** Small, and it is what makes single-trial
   detection viable at all.

1 and 3 are independent - two people, parallel, meeting only at
[`src/contract.py`](src/contract.py).

---

## 6. Where the Python in this folder fits

Your production path is a phone app; the Python here is not that app. It is the
**contract, the mock, and the test harness** - it lets you validate the whole event flow
today, and it defines the JSON your React Native app must produce. When the phone app is
ready it replaces `bridge.py` and speaks the same `SpikeEvent`, unchanged.
