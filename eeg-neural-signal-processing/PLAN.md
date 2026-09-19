# The Plan

Covers: the science question you asked, a build plan for neural signature validation,
a build plan for the retrospective-capture device, what to do before you arrive, and an
hour-by-hour for the event itself.

---

## 1. What you can actually rely on

You said you have no EEG hardware. Two things change that assessment:

1. **HackMIT stocks EEG.** The 2026 hardware list includes OpenBCI Ganglion (4-ch) and
   Cyton (8-ch), the Ultracortex Mark IV, an EEG Headband Kit, gold cup electrodes with
   Ten20 paste, Emotiv Insight and EPOC X, a Neurosity Crown, and a NeuroSky MindWave
   Mobile 2. All of it is flagged **Restricted** and governed by a separate "Biosignal
   and Wearable Device Protocol." See
   [HACKMIT-HARDWARE-REALITY-CHECK.md](HACKMIT-HARDWARE-REALITY-CHECK.md).
2. **BrainFlow has a synthetic board.** You can write and test the entire acquisition,
   filtering, feature, and classification pipeline right now against generated data,
   then change one board-ID constant when you get real hardware. This is the single
   highest-leverage thing you can do in the weeks before the event.

So the plan is: **build against datasets and the synthetic board now, swap in real
hardware at hour zero of the event.** Hardware becomes an upgrade, not a dependency.

---

## 2. Is a neural signature really unique?

Short answer: **yes, uniqueness is real and well-supported - but uniqueness is not the
property that makes a biometric good, and EEG is weak on the properties that matter.**

Biometrics are judged on four axes. EEG scores very differently on each.

### Uniqueness - strong

- The CEREBRE protocol (Ruiz-Blondet, Jin & Laszlo, *IEEE TIFS* 2016) drove event-related
  potentials from multiple functional brain systems at once and reached **100%
  identification accuracy in a pool of 50 users**.
- Graph-connectivity "BrainPrint" methods reach **98.82% on the 109-subject PhysioNet
  motor-imagery set using only 4 electrodes**.
- Resting EEG band power is **highly heritable** - averaged heritability estimates of
  roughly 76% (delta), 89% (theta), 89% (alpha), 86% (beta). High heritability is a
  double-edged result: it means the trait is *stable*, but it also means relatives
  resemble each other, which erodes distinctiveness.
- Even so, **monozygotic twins can be told apart**, particularly using signals from
  later-developing cortical areas, which are shaped more by individual experience than
  by genotype.

Caveat on all of this: pool sizes are 20-109 people. Fingerprint systems are evaluated
against millions. 100% on 50 subjects tells you very little about 50 million, because
false-match rate grows with database size.

### Permanence - this is the fatal weakness

This is the number that decides the project:

| Condition | Reported performance |
|---|---|
| Same session (enroll and test minutes apart) | ~97% accuracy, EER ~5.3% |
| Different session (enroll one day, test another) | **~34% accuracy, EER ~22%** |
| 1 day later | EER ~7.7% |
| 1 year later | EER ~19.7% |

For comparison, deployed fingerprint systems operate around 0.1% EER or better.

The cause is not that your brain changed. It is that **electrode placement, skin
impedance, hair, hydration, caffeine, fatigue, and mental state all changed** - and a
large part of what these models learn is the recording setup, not the person. This is
called template aging, and it is the open problem in the field, not a detail.

**Practical consequence:** if you demo this, enroll and test in the same session and you
will get a beautiful number that means nothing. Enroll on Saturday and test on Sunday and
it may well fail on stage. Plan for that.

### Collectability - poor

Ten seconds and a fingerprint reader, versus several minutes of gel, electrode
placement, impedance checking, and sitting still. This alone rules EEG out for phone
unlock. It does not rule it out for high-assurance, low-frequency access (a vault, a
weapons system, a clinical override) where a two-minute ceremony is acceptable.

### Anti-spoofing - this is your genuine edge, and your instinct is right

Your framing is correct and worth stating precisely:

- **A dead person cannot produce it.** Brain death presents as electrocerebral silence - the formal criterion is no non-artifactual cerebral activity above 2 µV peak-to-peak
  over at least 30 minutes on a scalp montage. There is literally no signal to present.
  (Note for accuracy: the AAN's updated guidance no longer recommends EEG as the
  ancillary test for determining brain death, because sedatives, hypothermia, and
  metabolic states can also flatten it. That does not weaken your point - it strengthens
  it. Anything that flattens EEG also means the person cannot authenticate.)
- **It is not left behind.** You shed fingerprints onto every surface you touch and your
  face is photographed constantly. Your EEG is not deposited anywhere.
- **It requires cooperation.** ERP-based protocols need the person to actually attend to
  a stimulus. An unconscious or unwilling person produces a degraded response - which
  means the *failure* is itself a duress signal, a property no other biometric has.

Now the three things that are usually left out of this pitch, which you should know
before you build on it:

1. **Liveness protects the sensor, not the wire.** Intrinsic liveness defeats a
   *presentation* attack (holding something up to the sensor). It does nothing against an
   *injection* attack, where a recorded EEG trace is replayed into the software below
   the digitizer. That is a solved-ish problem - there is published work on
   residual-feature replay detection for brainprint systems - but it means "unspoofable"
   is wrong. The correct claim is "no presentation attack exists."
2. **You cannot revoke your brain.** If a template leaks, you cannot issue a new head.
   The mitigation is **cancelable biometrics**: store only a non-invertible transform of
   the features under a random key, so a compromised template is revoked by reissuing
   the key. Build this in from the start - it is maybe 30 lines and it is the difference
   between a demo and a defensible design.
3. **Raw EEG is health data.** It carries markers of epilepsy, sleep disorder, substance
   use, and cognitive state. Storing raw EEG as an auth template creates a privacy
   liability that a fingerprint hash does not. Never persist raw traces; extract, hash,
   discard.

### Verified on real data

Every claim in this section was checked against 754 MB of downloaded EEG from 129
subjects across two public datasets. All of it held. See [RESULTS.md](RESULTS.md) - notably: closing your eyes between enrollment and test nearly triples EER on identical
hardware, and going from a 64-channel cap to 8 consumer electrodes costs 36 points of
accuracy.

### The verdict

Neural signature validation is a **real, publishable, worth-pursuing idea** - as a
research project over months, where you can run enrollment sessions weeks apart and
report honest cross-session numbers. That is a paper.

It is a **bad hackathon project**, because the thing that makes it interesting is
invisible in a demo and the thing that is visible in a demo is worse than a fingerprint
reader.

Keep the code. Use it as wearer verification inside project B (see §4).

---

## 3. Build plan - Neural Signature Validation (if you pursue it later)

Doing this properly, in order.

### Phase 0 - Data (do this first, it has lead times)

| Dataset | Subjects | Hardware | Why it matters | Access |
|---|---|---|---|---|
| [Auditory Evoked Potential EEG-Biometric](https://physionet.org/content/auditory-eeg/1.0.0/) | 20 | **OpenBCI Ganglion, 4 ch (T7, F8, Cz, P4), 200 Hz** | Built on hardware HackMIT actually stocks. 240+ 2-min recordings, resting eyes open/closed plus 6 auditory conditions. CSV + WFDB. | Open, direct download |
| [BED: Biometric EEG Dataset](https://zenodo.org/records/4309472) | 21 | Emotiv EPOC+, 14 ch, 256 Hz | **The only one with 3 sessions spaced a week apart.** The one that lets you measure cross-session honestly. | **RESTRICTED** - Zenodo access request to the authors. Apply now. |
| [EEG Motor Movement/Imagery (EEGMMIDB)](https://www.physionet.org/content/eegmmidb/1.0.0/) | 109 | 64 ch, 160 Hz | The field's standard biometrics benchmark. Your numbers are comparable to published ones. | Open, direct download |

Start with the auditory set (small, clean, 4-channel, matches your likely hardware).
Use EEGMMIDB to prove the method scales to 109 people. Use **BED to report the number
that actually matters** - enroll on session 1, test on session 3.

### Phase 1 - Pipeline

1. Load with **MNE-Python** (`mne.io.read_raw_edf` / from CSV via `mne.io.RawArray`).
2. Band-pass 1-40 Hz, notch at 60 Hz (US mains). Re-reference to average or mastoid.
3. Reject epochs by peak-to-peak amplitude (>100 µV is almost always artifact, see §5).
4. Epoch: 1-4 s windows for resting-state; stimulus-locked epochs for the auditory set.

### Phase 2 - Two models, run both

- **Baseline (do this first, it will surprise you):** per-channel band power in delta /
  theta / alpha / beta / gamma, plus spectral edge frequency and Hjorth parameters →
  features → an LDA or linear SVM. On 4 channels this is ~40 features. It trains in
  under a second and is frequently within a few points of the deep model. It is also
  interpretable, which matters when you have to explain a failure.
- **Deep:** **EEGNet** via [Braindecode](https://braindecode.org/), which takes
  `mne.Epochs` directly and ships pretrained checkpoints. Compact CNN designed exactly
  for this: temporal filters, then spatial filters, then depthwise-separable convolution.

### Phase 3 - Evaluate like a biometrician, not like a classifier

This is where most projects in this space quietly cheat. Report all four:

- **Closed-set identification accuracy** (who is this, from N known people) - the easy number.
- **Verification EER** (is this who they claim) - the honest number. Plot the DET curve.
- **Cross-session EER** - train on session 1, test on session 3 of BED. This is *the* number.
- **Open-set rejection** - hold out 5 subjects entirely, never seen in training. Can the
  system say "I don't know you"? A system that cannot is not an auth system.

### Phase 4 - Make it defensible

- **Cancelable template:** project features through a random-key matrix, quantize, hash.
  Store the hash only. Reissue the key to revoke.
- **Replay detection:** a replayed trace has no session-specific noise floor and no
  electrode-impedance drift. Check for exact-repeat correlation against the enrolled
  trace - a genuine sample is never a bit-identical match to a stored one.
- **Never store raw EEG.** Extract features in memory, hash, discard the trace.

---

## 4. Build plan - Retrospective Capture (the one to build)

**One-line pitch:** A wearable camera that records nothing - until your body says
something just happened, and then it keeps the last two minutes.

**Why the trigger is the whole invention.** SenseCam already proved that reviewing images
of your own day restores autobiographical memory in amnesia and mild Alzheimer's. Its
flaw was that it captured continuously and indiscriminately, producing thousands of
useless images a day and an obvious surveillance problem. Event-gating fixes both at
once: it is the retrieval solution *and* the privacy solution. Default is discard.

### Architecture

```
  ┌─── camera ──────────────┐
  │  continuous encode      │──▶ ring buffer (last 120 s, RAM or segment files)
  └─────────────────────────┘              │
                                            │  freeze + commit
  ┌─── trigger fusion ──────┐               ▼
  │  EEG   (frontal/temporal)  ├──▶ score ──┤  episode/
  │  PPG   (HR, HRV)           │            │    clip.mp4  (t-120s .. t+30s)
  │  IMU   (motion, falls)     │            │    signals.csv
  │  audio (SPL, distress)     │            │    caption.txt  ◀── VLM on Jetson/Pi
  │  manual (jaw clench, blink)│            └──────────────┘
  └────────────────────────────┘                   │
                                                    ▼
                                    queryable episode log + caregiver summary
```

Every element in that diagram maps to something on HackMIT's stock list. Details in
[HACKMIT-HARDWARE-REALITY-CHECK.md](HACKMIT-HARDWARE-REALITY-CHECK.md).

### Build order (each step is independently demoable - this is deliberate)

1. **Ring buffer + manual trigger.** Camera writes rolling H.264 segments; a button
   commits the last 120 s. *This alone is a working product.* Get here first, by hour 8.
   ~2 min of 640×480 @ 15fps is roughly 10-20 MB; use `ffmpeg -f segment` or GStreamer's
   `splitmuxsink`, or picamera2's circular output on a Pi.
2. **Deliberate biosignal trigger.** Replace the button with a **double eye-blink or a
   jaw clench** read off the EEG board. These are large, unambiguous signals - hundreds
   of µV against 10-100 µV of brain activity - and they are detectable at ~90% accuracy
   on hardware as cheap as a NeuroSky. This is your reliable stage demo.
3. **Passive physiological trigger.** Now add the real thing: a fusion score over frontal
   theta/alpha, heart-rate elevation and HRV drop from the MAX30102, and IMU agitation.
   Threshold on the fused score. Be explicit in the pitch that this is the research
   frontier, not a solved problem - multimodal agitation detection in dementia is an
   active area (Empatica E4 and EmbracePlus studies) with real results but no
   off-the-shelf answer.
4. **Make the buffer queryable.** This is the feature that turns a gadget into a product.
   Run a VLM over each committed clip to produce a caption, then let the wearer or
   caregiver ask "where did I leave my keys?" or "what upset him this afternoon?" and
   search the captions. On a Jetson Orin Nano Super you can do this on-device; on a Pi 5
   caption a few keyframes.
5. **Caregiver end-of-day summary.** N episodes, timestamps, captions, the physiological
   trace at each. This is the slide that wins.
6. **Wearer verification.** The EEG biometric fold-in - 60 s enrollment at start of day,
   then a periodic 1:1 check that the device is on the enrolled person. Frame it as
   privacy and correctness ("this device will not log a stranger"), and quote a realistic
   same-session EER (~5%), not 100%.

### Demo script (three minutes)

1. Wear it. Show the live feed and an empty `episodes/` directory. *"It is recording
   nothing. That directory stays empty all day."*
2. Trigger it (jaw clench or staged agitation). A clip appears.
3. Play the clip - it starts **before** the trigger. That is the whole idea and it lands
   instantly with an audience.
4. Ask the system a question about what it saw. It answers from the caption index.
5. Show the caregiver summary. Show the storage counter: X MB today instead of Y GB.

Step 3 is the moment. Rehearse it.

---

## 5. Your "sudden spike" question - what is actually detectable

"Spike" means at least five different things. Which one you mean changes the whole build.

| Phenomenon | Timescale | Amplitude | Detectable on 4-ch consumer EEG? |
|---|---|---|---|
| **Interictal epileptiform discharge** (the clinical "spike") | 20-70 ms | 50-200 µV | Sometimes, if frontally dominant. Needs annotated data (TUH). |
| **Seizure onset** | seconds | large | Yes for generalized; poorly for focal on 4 channels. |
| **P300** (salience/oddball) | ~300 ms post-stimulus | 5-20 µV | Only by averaging many trials, and best at Pz - which glasses cannot reach. |
| **ERN / error-related negativity** (you just made a mistake) | 50-100 ms post-error | 5-10 µV | Frontocentral, so partially reachable. Still needs averaging. Conceptually the most interesting one for dementia - it is the brain's "wait, that was wrong" signal. |
| **Alpha desynchronization** (8-13 Hz power drops when you engage) | hundreds of ms-seconds | robust | **Yes.** Single-trial detectable, works on few channels. Your most reliable passive signal. |
| **Blink / jaw clench / eyebrow raise** | 100-500 ms | 100s of µV to mV | **Yes, trivially, ~90% accuracy.** |

**The uncomfortable truth you need to design around:** in a loud convention hall, on a
dry-electrode headset, on a person who is moving, most of what looks like a "sudden
neural spike" is muscle. EMG from jaw and neck spreads across the entire scalp and
dominates everything above ~15 Hz. Eye blinks produce large slow waves in delta and
theta. These artifacts are 10-100× larger than the neural signals you want.

So:

- **Do not** promise single-trial detection of a subtle cognitive event on 4 dry channels
  in a hackathon venue. It will not work and a knowledgeable judge knows it.
- **Do** make EEG one vote in a multimodal fusion, where PPG and IMU carry real weight.
- **Do** use the artifacts deliberately. A jaw clench as a hands-free panic button is not
  a compromise - it is a legitimate accessibility interface for someone who cannot
  reliably operate a button. Reframe it and it becomes a feature.
- **Do** state the limitation on a slide before a judge asks. Naming your own weakness is
  the strongest move available in a hackathon Q&A.

---

## 6. Before you arrive (the next few weeks - highest leverage work)

Confirm the event dates and rules yourself at [hackmit.org](https://hackmit.org) - I
could not extract them reliably.

**Week 1 - data and pipeline, no hardware needed**
- [ ] Download the auditory EEG-biometric set (open). **Request BED access on Zenodo - it is restricted, not open**, and the request goes to the authors by email.
- [ ] `pip install brainflow mne braindecode` and get **BrainFlow's synthetic board**
      streaming into a live plot. This is your hardware stand-in.
- [ ] Register for the **TUH EEG Corpus** at
      [isip.piconepress.com](https://isip.piconepress.com/projects/tuh_eeg/) - it needs a
      data-use agreement and approval takes days. Do it now even if you may not use it.
- [ ] Build the ring-buffer recorder on your laptop webcam. Prove the pre-roll works.

**Week 2 - the trigger and the fusion**
- [ ] Implement blink and jaw-clench detection against synthetic + recorded data.
- [ ] Implement band-power features + LDA. If BED access comes through, get a real
      cross-session number from it. Whatever it is, that number goes on your slide.
- [ ] Build the fusion scorer with pluggable inputs so unavailable sensors degrade
      gracefully instead of crashing.

**Week 3 - de-risk the venue**
- [ ] Read the Biosignal and Wearable Device Protocol if HackMIT publishes it in advance;
      email organizers if not. Ask specifically: can you record video of other attendees?
      This determines whether your demo uses a teammate or a volunteer.
- [ ] If you want the Meta glasses, install the **Meta Wearables Device Access Toolkit**
      developer preview and get a trivial camera-capture app running on your own phone
      *before* the event. It requires extending an existing iOS/Android app - that is not
      a 2 a.m. task.
- [ ] Decide your fallback camera (USB webcam on a laptop) and make sure the whole demo
      runs on it with zero HackMIT hardware.

## 7. At the event

| Hours | Task |
|---|---|
| 0-1 | **Hardware desk immediately.** Everything you need is Restricted. Claim: an OpenBCI board, the Neurosity Crown if free, a Pi 5 or Jetson Orin Nano, a Pi Camera Module 3, MAX30102, and a set of eyeglass frames. Queues for restricted gear get long. |
| 1-3 | Get real EEG streaming. Swap the synthetic board ID for the real one. Check impedance. Confirm you see alpha increase when you close your eyes - that is the classic sanity check, and if you cannot see it your electrodes are bad. |
| 3-8 | Ring buffer + manual trigger running end to end on the target board. **Freeze this as your guaranteed demo.** Tag it in git. |
| 8-14 | Biosignal trigger (blink/clench). Add PPG and IMU to the fusion. |
| 14-20 | VLM captioning and the query interface. This is the differentiator; give it real time. |
| 20-26 | Caregiver summary UI. Instrument the storage/compute counters so your sustainability claim has actual numbers behind it. |
| 26-30 | Wearer verification, if time remains. Cut it without hesitation if anything above is shaky. |
| 30-34 | **Rehearse the demo six times.** Different lighting, different person, battery unplugged. Record a video of a successful run as insurance. |
| 34-36 | Slides, submission, sleep. |

**Kill criteria - decide these in advance so you are not deciding them at 3 a.m.:**
- No clean EEG signal by hour 6 → drop EEG entirely, run the trigger on PPG + IMU +
  audio. The project still works and the story barely changes.
- VLM not running on-device by hour 20 → call a cloud API and say so honestly.
- Wearer verification not working by hour 30 → cut it. It is the least important feature.

---

## 8. Resources

**Datasets** - full catalog with access notes in
[EEG-SENSORS-AND-DATASETS.md](EEG-SENSORS-AND-DATASETS.md)

**Software**
- [MNE-Python](https://mne.tools) - loading, filtering, epoching, artifact rejection
- [BrainFlow](https://brainflow.readthedocs.io) - one API for OpenBCI, Neurosity, Muse,
  plus the **synthetic board** for hardware-free development
- [Braindecode](https://braindecode.org) - EEGNet and other architectures, takes MNE
  objects directly, ships pretrained checkpoints
- [Neurosity SDK](https://neurosity.co) - JS and Python, raw EEG at 256 Hz, on-device
  processing, signal quality as an observable stream. Best developer experience of any
  device on the list.
- [Emotiv Cortex API](https://emotiv.gitbook.io/cortex-api) - WebSocket/JSON. **Read the
  licensing note in the hardware doc before relying on it.**

**Key papers**
- Ruiz-Blondet, Jin & Laszlo (2016), *CEREBRE: A Novel Method for Very High Accuracy
  Event-Related Potential Biometric Identification*, IEEE TIFS - the 100%/50-subject result
- *A Survey on Brain Biometrics*, ACM Computing Surveys - the field overview
- Hodges et al., SenseCam papers (Microsoft Research) - the evidence base for project B
- *Multimodal Detection of Agitation in People With Dementia*, JMIR Aging 2025 - the
  closest published prior art to your trigger
