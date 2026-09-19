# HackMIT 2026 Hardware - Reality Check

Read against the [official 2026 hardware list](https://docs.google.com/document/u/0/d/1zsWBykCCE60JHEBntNcSprbEEqtpPu7GZDfIOWIws0Q/mobilebasic).
Verdict: **almost everything both projects need is stocked.** Three things will quietly
kill you if you don't plan for them.

---

## The headline: you were wrong about having no hardware

You assumed you were dataset-only. HackMIT stocks a full EEG lab:

**Biosignal and Physiological Sensing** *(all Restricted)*
- OpenBCI **Ganglion (4-ch)** and **Cyton (8-ch)** biosensing boards
- OpenBCI Biosensing Starter Bundle, **EEG Headband Kit**, **Ultracortex Mark IV**
- OpenBCI **gold cup electrodes and Ten20 conductive paste** ← wet electrodes, good data
- **Emotiv Insight** and **Emotiv EPOC X**
- **Neurosity Crown**
- **NeuroSky MindWave Mobile 2**
- MyoWare 2.0 surface EMG, analog EMG modules
- AD8232 single-lead ECG, MAX30101/MAX30102 pulse oximetry and PPG
- Disposable surface electrodes and adhesive pads

That is six different EEG systems. Plan to use them.

---

## The three things that will kill you

### 1. Everything you need is "Restricted" - go to the hardware desk at hour zero

Every EEG device, every wearable, every battery, and the cameras you want are flagged
Restricted. Biosignal and wearable gear is additionally governed by a separate
**"Biosignal and Wearable Device Protocol."**

Practical consequences:
- **Queues.** There are more teams than Neurosity Crowns. Go first, before you write a
  line of code. Claim your board, then build.
- **Read the protocol.** Email organizers beforehand and ask specifically: **may you
  record video of other attendees?** Your demo design depends on the answer. Plan to
  record only teammates and consenting volunteers.
- The list is explicit that these are acquisition-only devices - **no stimulation, no
  TENS**, nothing delivering current to the body. Do not propose anything that stimulates.

### 2. The Emotiv EPOC X licensing trap

EPOC X has 14 channels, the most of anything on the list, so it is the obvious grab.
But Emotiv gates **raw EEG behind a paid Developer API license** on its professional
devices. The Basic BCI API is free; the Raw EEG API and high-resolution performance
metrics are not. The consumer **Insight** exposes all data streams to the free SDK.

If HackMIT's EPOC X units don't have an active license attached, you get processed
metrics and no raw signal - which kills any biometrics or custom-feature work.

**Ask at the desk, in the first hour: "is there a Developer API license on these?"**
If the answer is no or unclear, take OpenBCI or the Crown instead.

### 3. The Meta glasses are not what you think

Stocked: **Meta Ray-Ban AI glasses (Gen 1 / Gen 2)** and **Meta Ray-Ban Display with
Neural Band**, plus "research smart glasses provided under a manufacturer research
program, if available."

What you actually get through the Meta Wearables Device Access Toolkit:
- The 12 MP ultra-wide camera, the 5-mic array, and open-ear speakers
- Access by **extending an existing iOS/Android app** - your code runs on the phone,
  not on the glasses
- Still developer preview; no storefront publishing

What you do **not** get:
- **Raw sEMG from the Neural Band.** Meta exposes recognized gestures through proprietary
  algorithms; raw voltages are inaccessible. The Neural Band is a gesture pad, not a
  biosignal sensor you can build features on.
- Any ability to run code on the glasses themselves
- Any way to physically modify them for electrodes

**If you want the Meta glasses in your demo, install the toolkit and get a trivial
camera-capture app running on your own phone before the event.** Setting up a mobile
toolchain at 2 a.m. is how teams lose a night.

### The item on the list that solves your glasses problem

> **"Non-prescription eyeglass frames used as wearable-prototype platforms"**

Stocked explicitly for building instrumented eyewear. This is the right substrate for the
"glasses as electrode clamp" idea - not a sealed Ray-Ban. See
[GLASSES-PLUS-EEG-IDEAS.md](GLASSES-PLUS-EEG-IDEAS.md).

---

## Everything else you need, and where it comes from

### Compute
- **NVIDIA Jetson Orin Nano Super Developer Kit** - the one to grab if you want on-device
  VLM captioning. Real GPU inference at the edge, which makes the "no video leaves the
  device" privacy claim true rather than aspirational.
- **Raspberry Pi 5 (4/8/16 GB)** with active cooler - the safe choice. Runs the ring
  buffer and camera comfortably; caption a few keyframes rather than full video.
- Pi Zero 2 W, Pi Pico 2, **Seeed XIAO ESP32-S3**, ESP32-S3-DevKitC-1 - for the
  wearable/frame-side microcontroller
- Teensy 4.1, Arduino Portenta C33, Nicla Vision, Nicla Voice

### Cameras
- **Raspberry Pi Camera Module 3** (autofocus, wide-angle variants) - the default choice
- **ESP32-CAM / ESP32-CAM-MB** - tiny, wearable, but low quality and awkward to drive
- **USB webcams (1080p / 4K)** - your zero-risk fallback. Make sure the demo runs on one.
- Luxonis OAK-D Lite (on-board AI), Intel RealSense D435 series (depth) - both Restricted

### Sensors for the fusion trigger
- **MAX30101 / MAX30102** pulse oximetry and PPG → heart rate, HRV. **The most valuable
  non-EEG signal for agitation and stress detection**, and far more robust than EEG in a
  noisy venue.
- **AD8232** single-lead ECG → cleaner HRV than PPG if you can tolerate chest electrodes
- **BNO085 / BNO055 / MPU-9250** IMUs → agitation, falls, wandering, gait
- **ReSpeaker 4-Mic Array** or ReSpeaker USB Mic Array → sound pressure level, distress
  vocalization, voice queries
- **MyoWare 2.0** surface EMG → an alternative jaw-clench or gesture trigger
- PIR motion, VL53L1X time-of-flight, TEMT6000 ambient light

### Feedback and interface
- **DRV2605L haptic driver + LRA / coin motors** → the gentle reorientation cue
- E-ink display, OLED/TFT breakouts, Pi 5" HDMI touchscreen, portable 15.6" USB-C monitor
  (use this for the demo dashboard)
- MAX98357A I2S amp + small speakers, piezo buzzers

### Power
- Single-cell 3.7 V LiPo, ~1,000-6,600 mAh, JST *(Restricted)*
- USB power banks ~10,000 mAh, and packs sized for Pi/Jetson *(Restricted)*
- **TP4056 / Micro-Lipo USB-C charge and protection modules** *(Restricted)* - you want
  these for anything battery-powered and wearable
- DC-DC buck/boost converters

### Fabrication
- 3D printing is not on the list - **do not plan a printed enclosure.** Use the stocked
  eyeglass frames, foam board, velcro, zip ties, and gaffer tape. Hot glue is restricted
  to a designated bench, so factor in the walk.

---

## Recommended kit list - walk up and ask for this

**Core (get these first):**
1. Neurosity Crown *or* OpenBCI Cyton - whichever is available
2. OpenBCI Ganglion as the frame-mounted backup
3. Gold cup electrodes + Ten20 paste (wet contacts if you want data that isn't garbage)
4. Raspberry Pi 5 (8 GB) + active cooler + 27 W supply + 128 GB microSD
5. Raspberry Pi Camera Module 3 (wide)
6. MAX30102 PPG breakout
7. BNO085 IMU
8. Non-prescription eyeglass frames ×2

**Nice to have:**
9. Jetson Orin Nano Super - only if a teammate is confident with the Jetson toolchain;
   it will eat hours otherwise
10. DRV2605L + LRA haptic
11. Portable 15.6" USB-C monitor for the demo station
12. LiPo + TP4056 for the untethered version

**Fallback, cost nothing to hold:**
13. NeuroSky MindWave Mobile 2 - one channel, but enough for a blink/clench trigger if
    every good headset is claimed
14. A USB webcam - guarantees the demo runs even if all EEG hardware fails

---

## Feasibility verdict

| Component | Feasible in 36 h? | Note |
|---|---|---|
| Ring buffer + manual trigger | **Yes, easily** | Do it on your laptop before the event |
| Blink / jaw-clench EEG trigger | **Yes** | Large signals, ~90% accuracy on cheap hardware |
| PPG + IMU fusion trigger | **Yes** | Both breakouts are stocked and well-documented |
| Passive EEG "distress" detection | **Partly** | Works as one weighted vote. Do not claim single-trial accuracy. |
| On-device VLM captioning | **Yes on Jetson, tight on Pi 5** | Have a cloud API fallback wired up |
| Instrumented eyeglass frame | **Yes** | Frames are stocked for exactly this |
| Wearer verification (EEG biometric) | **Yes, same-session** | Quote ~5% EER honestly, not 100% |
| Ray-Ban camera integration | **Only if pre-built** | Toolkit app must exist before you arrive |
| Raw sEMG from the Neural Band | **No** | Not exposed. Gestures only. |
| Cross-session EEG authentication | **No** | ~34% cross-session accuracy. Do not build a demo on this. |
