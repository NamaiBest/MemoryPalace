# glasses-software

For the current **EEG → stop recording** build, use
[hardware-demo/](../../hardware-demo/), including its prepared Meta Android companion.
This folder retains the earlier capture-after-trigger prototype.

The glasses half of the system. Knows nothing about EEG.

`confusion-detector/` (and any future spike detector) is the ML half. It knows nothing
about Meta's SDK. The two meet at exactly one file: [`src/contract.py`](src/contract.py).

That split is the point. Two people can work in parallel; either half can be tested
alone; swapping mock hardware for real glasses changes one flag.

**Read [PIPELINE.md](PIPELINE.md)** for the end-to-end design and the hardware answers.
**Read [CAPTURE_MODULE.md](CAPTURE_MODULE.md)** for the real capture-trigger API, verified
against Meta's own sample code - photo burst vs. video, why the app is React Native
plus one native module (not pure Kotlin or pure RN), and the actual startup latency
you need to budget for.

**Scope: semantic difficulty (N400) only.** One signal, one sensor, one detector. No
startle/IMU path, no microcontroller - the phone is the brain.

**Headset: Neurosity Crown** (BLE + official React Native SDK, free raw EEG,
centro-parietal coverage), with Emotiv Insight as backup. **Emotiv EPOC X is blocked** -
raw EEG on professional Emotiv hardware needs a paid Developer licence, and it has no
midline/CP electrodes for N400.

## Run it now, with no hardware

```bash
python3 demo_end_to_end.py --seconds 5          # ML calls device in-process

# or the real topology, two processes:
python3 -m src.bridge --device mock --port 8770
python3 demo_end_to_end.py --via-bridge --seconds 5
```

Works today. No glasses, no phone, no Meta account, no EEG. Uses the laptop webcam if
available and falls back to placeholder files if not.

## Structure

| File | Role |
|---|---|
| `src/contract.py` | **The boundary.** `SpikeEvent` + `CaptureResult`. Nothing else crosses. |
| `src/glasses/base.py` | Abstract device - deliberately tiny, because Meta's SDK exposes little |
| `src/glasses/mock.py` | Works today. Webcam or placeholder files. |
| `src/glasses/meta_dat.py` | Real glasses, via a companion phone app you must write |
| `src/bridge.py` | HTTP service: ML posts a spike, glasses record. Owns the cooldown. |
| `demo_end_to_end.py` | Proves the chain |

## Why the bridge is a separate process

If the detector crashes mid-session the capture service survives, and vice versa. The
cooldown also lives in the bridge rather than the detector, because the capture service
is the only component that knows what it is already busy doing.

## The catch you should know about up front

N400 is normally an *averaged* measurement - a consumer-headset study needed ~25 trials
for reliable detection. One hard word does not give one clean spike. PIPELINE.md §3
covers the two things that make it workable anyway: a real reading struggle produces
sustained effort *after* the N400 (same sensor, slower feature), and per-wearer
calibration.

## The one thing you cannot avoid

There is no Python path to the glasses. Meta's toolkit is a native mobile SDK, and the
only route is `your Kotlin app -> Meta AI companion app -> Bluetooth -> glasses`. So
`meta_dat.py` posts to a phone app that you write; it does not call Meta directly. See
PIPELINE.md §4.

Meta's **Mock Device Kit** simulates that whole SDK stack, so the Kotlin app is testable
before you ever hold the glasses.
