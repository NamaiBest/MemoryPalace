# Confusion Detector

For the current **EEG → stop recording** build and live Crown adapter, use
[hardware-demo/](../hardware-demo/). It reuses this detector's feature extraction
and persistence code. The experiment documented below takes photos on a trigger.

Notices when you have been stuck on something for a while, photographs what you were
looking at, and shows you the list afterwards.

**One-line pitch:** *it notices what confused you and shows you later.*

## Why this design

Two constraints shaped it, both of them things we measured rather than assumed.

**Battery.** A retrospective "dash cam" has to hold a rolling video buffer, which means
the camera runs continuously: roughly 30-45 minutes on Ray-Ban-class hardware. Dead on
arrival. But retrospection is only needed for *instantaneous* events. Sustained states
are still happening a second later, so we **capture forward**: camera stays off until a
trigger fires. (SenseCam, the wearable-camera research that actually helped dementia
patients, never recorded video either - it took a still every ~30 seconds.)

**Sustained, not transient.** Two independent analyses in this repo agree:
`eeg-neural-signal-processing/RESULTS.md` §10 got a usable trigger out of a *sustained*
state, while `xueqi-validation/RESULTS.md` §10-11 found a *transient* event trigger
(~200 ms surprise ERP) produced ~29 false alarms/hour. So this targets sustained
cognitive load, which is the regime that works.

## How it works

```
EEG (2-4 frontal electrodes)
  -> 4 s non-overlapping windows
  -> frontal theta/alpha  (theta rises with effort, alpha drops - ratio moves both ways)
  -> z-score against THIS wearer's calibrated baseline
  -> fire after k consecutive elevated windows      <- persistence filter
  -> take one photo, start a cooldown
  -> end of session: "here are the N things that held you up"
```

Frontal theta/alpha, not an ERP: band power over seconds tracks a state, and states are
what we can actually detect.

## Run it

Works with no hardware at all.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# no hardware, no camera
.venv/bin/python run_session.py --board synthetic --calibrate 120 --monitor 300 --no-camera

# validate the detector against known confusion episodes
.venv/bin/python simulate.py
.venv/bin/python simulate.py --sweep

# deterministic demo fallback (replays a fixture with 14 known episodes)
.venv/bin/python simulate.py --save fixtures/demo_session.npz
.venv/bin/python run_session.py --board playback:fixtures/demo_session.npz --fast \
    --calibrate 120 --monitor 1500 --artifact-uv 400 --label demo

# the team's Muse
.venv/bin/python run_session.py --board muse2 --calibrate 120 --monitor 900

# OpenBCI at HackMIT
.venv/bin/python run_session.py --board cyton --serial-port /dev/cu.usbserial-XXXX

# afterwards
.venv/bin/python review.py sessions/demo      # terminal summary + review.html
```

## The one result that matters

**Window overlap was silently destroying the persistence filter.**

The filter assumes consecutive windows are roughly independent evidence. With a 4 s
window and a 1 s hop they share 75% of their data, so "4 in a row" is really about 2
independent looks. Measured on identical data, changing *only* the hop:

| Overlap | Detection | False alarms/hr |
|---|---|---|
| 75% (hop 1 s) | 100% | 30.3 |
| 50% (hop 2 s) | 100% | 18.9 |
| **0% (hop 4 s)** | **100%** | **1.3** |

Same code, same threshold, 24x fewer false alarms. This is why `hop_s == window_s` in
`config.py`. My earlier §10 result used non-overlapping epochs; I ported the parameter
without porting the assumption, and it cost an order of magnitude.

## Honest performance numbers

The simulator generates EEG with scripted high-load episodes and runs the real
detector over it. Two versions, and the difference matters:

| Fixture | Detection | False alarms/hr | Latency |
|---|---|---|---|
| Stationary baseline | 100% | 1.3 | 13.6 s |
| **+ realistic slow drift (default config)** | **100%** | **7.2** | **15.7 s** |

Operating points under the realistic fixture (`simulate.py --sweep`):

| k | z | Detection | False/hr | Latency | |
|---|---|---|---|---|---|
| 3 | 2.0 | 100% | 8.9 | 11.7 s | faster, noisier |
| **4** | **2.0** | **100%** | **7.2** | **15.7 s** | **default** |
| 4 | 2.5 | 94.1% | 3.0 | 16.0 s | quieter, misses some |
| 5 | 2.5 | 91.2% | 2.5 | 19.7 s | quietest usable |

Hop 6 s (i.e. *gaps* between windows) was worse everywhere - it starts missing
episodes without buying quiet. Exactly-non-overlapping is the sweet spot.

Real EEG is not stationary - attention wanders, electrode impedance drifts. When the
fixture's baseline drifts realistically (load-index sd ~0.2-0.5 instead of an
implausible 0.04), false alarms rise roughly **6-10x** at a fixed threshold. Those are
the honest numbers, and they sit in the same range as Xueqi's independently-measured
~29/hour, which suggests that figure was realistic rather than pessimistic.

**7.2 false alarms/hour is still not a shippable product** - a spurious bookmark every
eight minutes. It is fine for a demo (you will trigger it deliberately) and it is a
reasonable starting point for a 24-hour build. What is solid is the *relative* finding
(overlap costs 24x), since that is a controlled comparison on identical data. Driving
the absolute rate down is the open problem - see below.

**And this is a simulator.** It validates the signal chain, the operating point, and the
overlap bug. It says nothing about whether *real* confusion produces this signature in a
*real* brain. That needs the headband.

## Which electrodes? (measured, see [CHANNELS.md](CHANNELS.md))

Two channels is enough **only if one sits on the midline top of the head**. Measured on
51 recordings of a real surprise dataset, within-subject:

| Montage | AUC |
|---|---|
| Cz+O1 (best pair of all 120) | 0.745 |
| Fz+Cz | 0.719 |
| Neurosity Crown (estimated) | 0.763 |
| Muse 2/S (estimated) | 0.680 |
| Glasses temples F7+F8 | 0.601 (rank 119 of 120) |

Every one of the top 12 pairs contains Cz or Fz. The two obvious glasses pairs rank
118th and 119th. **Use the Neurosity Crown** - it is on the HackMIT parts list, reaches
the positions that carry the signal, and a judge can put it on in ten seconds.

## What is not claimed

- That this reads confusion. It measures sustained frontal theta/alpha, which correlates
  with mental effort. Effort is not confusion, and neither is a diagnosis.
- That it works on Meta Ray-Bans. Those have no EEG.
- That a glasses-mounted 2-electrode build works for this. It does not - see
  [CHANNELS.md](CHANNELS.md). Frontal/temporal contacts are good for blink, jaw clench
  and drowsiness, and poor for surprise or cognitive load.
- That the simulated numbers transfer to real brains.

## Open problems

1. **Get false alarms below ~2/hour without losing detection.** (k=4,z=2.5 gets 3.0/hr but drops to 94%.) Options: a second modality as a confirming vote
   (heart-rate variability, or blink rate from the camera), an adaptive baseline that
   tracks slow drift instead of a fixed calibration, or requiring the elevation to be
   *sustained and rising*.
2. **Validate against real confusion**, with a reading task where comprehension is
   probed afterwards, so there is ground truth.
3. **Swap in the glasses camera.** `src/capture.py` is the only file that changes.

## Files

| File | What it does |
|---|---|
| `src/config.py` | Every tunable, with the measurement behind each default |
| `src/eeg_source.py` | Muse / OpenBCI / synthetic / playback, one interface |
| `src/cognitive_load.py` | Filtering, artifact rejection, theta/alpha index |
| `src/detector.py` | Per-wearer calibration + persistence filter |
| `src/capture.py` | Camera on trigger (the seam for the glasses SDK) |
| `src/session.py` | Calibrate -> monitor -> fire -> save |
| `run_session.py` | Live session |
| `review.py` | Terminal summary + self-contained `review.html` |
| `simulate.py` | Ground-truth validation and operating-point sweep |
| `src/surprise_channels.py` | Which electrodes carry the signal, on real data |
| `src/fetch_ds006394.py` | Downloads the surprise dataset (548 MB) |
| `CHANNELS.md` | The electrode/hardware answer, with numbers |
