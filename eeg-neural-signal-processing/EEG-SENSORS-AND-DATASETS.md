# EEG Sensors and Open Datasets

Everything you need to know about the hardware, and every dataset worth downloading.

---

## Part 1 - How an EEG sensor actually works

### First, the correction on "6-bit, 32-bit, 64-bit"

You are conflating three independent specs. Only one of them is usually what people
mean, and it is almost never the one that limits you.

**1. Channels - the number you actually meant.**

The count of electrodes on the scalp. This is what people mean by "an 8-channel" or
"a 64-channel" system. More channels means more *spatial* coverage - more places on the
head you are listening from - not finer detail in time or amplitude.

| Channels | Typical devices | What you can do |
|---|---|---|
| 1 | NeuroSky MindWave | Attention/meditation indices, blink detection. Toy-grade but genuinely works for that. |
| 4 | OpenBCI Ganglion, Muse | Frontal/temporal band power, blink and jaw detection, basic biometrics. Published work reaches ~98% identification on 4 well-chosen electrodes. |
| 5-14 | Emotiv Insight (5), EPOC X (14) | Adds coverage; enough for basic ERPs with averaging. |
| 8-16 | OpenBCI Cyton (8), Cyton+Daisy (16) | The practical research floor. Full 10-20 subsets, decent source separation. |
| 32-256 | Research caps (BioSemi, Brain Products, EGI) | Source localization, clinical work, competitive published results. |

**2. ADC bit depth - the "24-bit" you half-remembered.**

How finely each sample is quantized. **There is no 6-bit or 64-bit EEG ADC.** The
standard is 24-bit, and there is a good physical reason.

The TI **ADS1299** is the chip inside essentially every serious hobbyist and many
research EEG amplifiers - including the OpenBCI Cyton. It is a 24-bit sigma-delta ADC
purpose-built for biopotentials, with noise below 0.5 µV RMS. On the Cyton at gain 24
that works out to about **0.298 µV per bit**.

Why you need that: scalp EEG is roughly 10-100 µV, sitting on top of DC offsets and
drift that can be a thousand times larger. To resolve microvolt detail without clipping
on the offset, you need enormous dynamic range. 24 bits gives you it. 16 bits is the
absolute low end and you feel it.

**3. Sampling rate - how often, in Hz.**

- OpenBCI Ganglion: 200 Hz. Cyton: 250 Hz.
- Neurosity Crown, Emotiv EPOC+: 256 Hz.
- Research systems: 500-5000 Hz.

Note a real gotcha: the ADS1299 chip supports up to 16 kSPS, but **the Cyton is capped
at 250 Hz by its radio link**, not by the ADC. Adding the Daisy module for 16 channels
drops you to 125 Hz over Bluetooth (250 Hz if you log to the onboard SD card instead).

Nyquist says 250 Hz gets you clean content to ~125 Hz, which covers delta through
gamma. For everything in this project, 200-256 Hz is plenty.

### The rule of thumb

> **Electrode quality > channel count > sampling rate > bit depth.**

Four well-placed electrodes with good skin contact will beat sixty-four badly-placed dry
ones every time. Contact impedance is the thing that ruins recordings, and it is the
thing nobody talks about in spec sheets.

### The other specs that matter more than any of the above

**Wet vs. dry electrodes.** Wet (gold cup + Ten20 conductive paste) gets contact
impedance down to single-digit kΩ and gives you genuinely clean data. Dry electrodes are
10-100× worse and far more motion-sensitive, but you can put them on in ten seconds.
Every consumer headset is dry. This trade is the single biggest determinant of your data
quality. HackMIT stocks both: the Ultracortex uses dry pins, and gold cups with Ten20
are available if you want the good stuff.

**Reference and ground.** EEG measures a *difference*. Every channel is
"electrode minus reference," so where you put the reference changes every number you
record. Common choices are the mastoid (bone behind the ear), an earlobe clip, or the
average of all electrodes computed offline. You also need a separate bias/ground
electrode for common-mode rejection. Forgetting this is the number one reason a
first-time EEG rig produces garbage.

**The 10-20 system.** The standard naming scheme for electrode positions. Letter = lobe
(Fp=frontopolar, F=frontal, C=central, T=temporal, P=parietal, O=occipital), number = odd
on the left, even on the right, z = midline. So Fp1 is left forehead, Cz is the top of
your head, O1 is left back. You will see these names in every dataset and paper.

Positions relevant to this project:
- **Fp1, Fp2** (forehead) - enormous eye-blink and eye-movement signals, frontal theta
- **F7, F8, T7, T8** (temples) - temporalis muscle (jaw clench), frontal-temporal activity
- **Cz, Pz** (top/back of head) - where P300 is largest. **Not reachable from glasses.**
- **O1, O2** (back of head) - the cleanest alpha rhythm. Also not reachable from glasses.
- **A1/A2 or M1/M2** (mastoids/earlobes) - the standard reference sites

### Signal bands, and what each one tells you

| Band | Hz | Associated with | Watch out for |
|---|---|---|---|
| Delta | 0.5-4 | Deep sleep | **Eye blinks live here.** Most "delta" on a frontal channel is a blink. |
| Theta | 4-8 | Drowsiness, memory encoding, cognitive load | Genuinely useful for the fatigue/confusion trigger |
| Alpha | 8-13 | Relaxed wakefulness; **drops when you engage** (desynchronization) | Your most robust real signal. Largest at O1/O2 with eyes closed. |
| Beta | 13-30 | Active thinking, alertness | Starts to be contaminated by muscle |
| Gamma | 30+ | Widely hyped in consumer EEG | **Mostly muscle.** EMG dominates above ~15 Hz. Treat any gamma claim with suspicion. |

### The sanity check that will save you hours

Sit still, eyes open, watch the 8-13 Hz power on an occipital or even a frontal channel.
Close your eyes. **Alpha power should visibly jump within a second or two.** This is the
Berger effect, it is the oldest result in EEG, and it works on essentially every human.

If you cannot see it, your electrodes are bad. Do not debug your model - fix your
contact. Add paste, move hair out of the way, check the reference.

---

## Part 2 - Open datasets

### Best for biometrics / neural signature

**[Auditory Evoked Potential EEG-Biometric Dataset](https://physionet.org/content/auditory-eeg/1.0.0/)** - PhysioNet, DOI `10.13026/ps31-fc50`
- 20 subjects, 240+ recordings of 2 minutes each
- **OpenBCI Ganglion, 4 channels: T7, F8, Cz, P4, at 200 Hz**
- Resting state (eyes open and eyes closed) plus six auditory conditions: native song,
  non-native song, and neutral music, each delivered both in-ear and by bone conduction
- CSV and WFDB formats. Open access, no registration.
- **Why start here:** it was recorded on hardware HackMIT stocks, at a channel count you
  can realistically build, and two of its four electrodes (T7, F8) are reachable from a
  glasses frame. It is the tightest link between data you have today and hardware you
  might have at the event.

**[BED - Biometric EEG Dataset](https://zenodo.org/records/4309472)** - Zenodo, DOI `10.5281/zenodo.4309471`
- 21 subjects, Emotiv EPOC+, 14 channels at 256 Hz
- 12 stimuli across four types: affective, cognitive, visual evoked potential, resting state
- **Three sessions spaced one week apart** - this is the point of the dataset
- **Access is RESTRICTED**, despite being on Zenodo. You must submit an access request
  that goes to the authors. Budget days, not minutes. Apply before you need it.
- **Why it is essential:** it is the only one here that lets you measure cross-session
  performance honestly. Every within-session accuracy number in EEG biometrics is
  inflated; this dataset is how you find out by how much. If you build one evaluation,
  build this one.

**[EEG Motor Movement/Imagery Database (EEGMMIDB)](https://www.physionet.org/content/eegmmidb/1.0.0/)** - PhysioNet
- **109 subjects**, 64 channels, 160 Hz, 1,500+ recordings, BCI2000 system
- Motor and imagined-motor tasks plus two baseline (resting) runs
- Open access, direct download
- **Why:** the field's default benchmark. Published EEG biometric papers report on this
  set, so your numbers are directly comparable. Use it to show your method scales past
  20 people.

### Best for spike / event / seizure detection

**[CHB-MIT Scalp EEG Database](https://physionet.org/content/chbmit/1.0.0/)** - PhysioNet
- 23 pediatric subjects (ages 1.5-22), 256 Hz, ~940 hours of continuous recording
- Expert-annotated seizure onsets and offsets
- Open access. Collected at Boston Children's / MIT - a nice detail for a HackMIT pitch.
- The standard starting point for seizure detection.

**[TUH EEG Corpus](https://isip.piconepress.com/projects/tuh_eeg/)** - Temple University
- The largest open clinical EEG corpus: 15,000+ subjects, mostly 250 Hz
- **TUSZ** (seizure corpus): 280+ patients, 3,500+ annotated seizure events across eight
  seizure types, 5M+ seconds of recording
- **TUEV** (events corpus): annotations for spikes and sharp waves, GPED, PLED, eye
  movement, and artifacts - **the right dataset if you want a literal "spike" detector**
- **Requires free registration and a data use agreement.** Approval takes days. If you
  want this, apply now.

### Best for emotion and mental state

- **[DEAP](https://www.eecs.qmul.ac.uk/mmv/datasets/deap/)** - 32 subjects, 32 channels,
  music-video stimuli with valence/arousal/dominance ratings. Requires an EULA.
- **[SEED](https://bcmi.sjtu.edu.cn/home/seed/)** - SJTU, film-clip emotion elicitation,
  62 channels. Requires an application.
- **[LEMON (MPI Leipzig Mind-Brain-Body)](https://www.mpi.cbs.mpg.de/)** - large
  resting-state, 62 channels, with extensive behavioral and physiological phenotyping.
- **[ERP CORE](https://erpinfo.org/erp-core)** - 40 subjects, **seven standard ERP
  paradigms** (N170, MMN, N2pc, N400, P3, LRP, ERN) with raw data, processed data, and
  analysis scripts. **This is the best resource for learning what an evoked "spike"
  actually looks like** - and it includes the ERN, the error-detection component, which
  is conceptually the closest thing to a "something just went wrong" signal.

### General repositories

- **[OpenNeuro](https://openneuro.org/search/modality/eeg)** - hundreds of BIDS-formatted
  EEG datasets, all open, all downloadable via CLI
- **[PhysioNet](https://physionet.org/content/?topic=electroencephalogram)** - browse by
  EEG topic
- **[MOABB](https://neurotechx.github.io/moabb/)** - Mother of All BCI Benchmarks;
  wraps a dozen motor-imagery and P300 datasets behind one Python API with standardized
  evaluation. Saves days of data-wrangling.
- **[MindBigData](https://mindbigdata.com/)** - very large single-subject collections
  from consumer devices

### Access reality check

| Dataset | Registration | Lead time |
|---|---|---|
| Auditory EEG-Biometric, EEGMMIDB, CHB-MIT | None | Immediate |
| **BED (Zenodo)** | **Access request to authors** | **Days - apply now** |
| ERP CORE, OpenNeuro | None | Immediate |
| **TUH / TUSZ** | Data use agreement | **Days - apply now** |
| DEAP, SEED | EULA / application | Days to weeks |

The auditory biometric set, EEGMMIDB, CHB-MIT and ERP CORE are all genuinely open and
download immediately. Apply for **both TUH and BED** now - they are the two that gate
the interesting evaluations, and both take days.

---

## Part 3 - Devices, compared

Only devices HackMIT actually stocks. Prices for context, not because you are buying.

| Device | Ch | Rate | Electrodes | SDK | Verdict for a 36-hour build |
|---|---|---|---|---|---|
| **Neurosity Crown** | 8 | 256 Hz | Dry | JS + Python, observable streams, raw EEG + focus/calm + signal quality | **Best developer experience by a wide margin.** On-device processing. Fastest path to something working. Grab it if it is free. |
| **OpenBCI Cyton** | 8 | 250 Hz | Wet or dry | BrainFlow (Python/C++/Java/JS) + OpenBCI GUI | **Best data quality and most control.** ADS1299, 24-bit, 0.298 µV/bit. The serious choice. |
| **OpenBCI Ganglion** | 4 | 200 Hz | Wet or dry | BrainFlow | Smaller, lighter, cheaper. **Matches the auditory biometric dataset exactly.** Best candidate for a glasses build. |
| **Emotiv Insight** | 5 | 128 Hz | Semi-dry | Cortex API (WebSocket/JSON) | Fine. All data streams available to the Developer SDK on consumer devices. |
| **Emotiv EPOC X** | 14 | 256 Hz | Saline felt | Cortex API | **Careful - raw EEG requires a paid Developer API license.** Basic BCI API is free; the Raw EEG API is not. Verify before you build on it. |
| **NeuroSky MindWave 2** | 1 | 512 Hz | Dry, single | ThinkGear serial | One channel. Fine as a blink/jaw-clench trigger and a good fallback, useless for anything spatial. |
| **OpenBCI Ultracortex Mk IV** | up to 16 | - | Dry pins | via Cyton/Daisy | The 3D-printed headset shell. Takes 10-20 min to fit properly. Budget that time. |

### The Emotiv licensing trap, stated plainly

EPOC X is the highest channel count on the list, so it is the obvious grab. But raw EEG
access on Emotiv's *professional* devices sits behind a paid Developer API license, while
the consumer Insight exposes all data streams to the free SDK. If HackMIT's units do not
have an active license attached, you get processed metrics and no raw signal - which
kills a biometrics or custom-feature build.

**Check this at the hardware desk in the first hour**, not at hour twenty.

### Recommended stack for this project

- **Primary:** Neurosity Crown (speed) or OpenBCI Ganglion (control + dataset match)
- **Library:** BrainFlow - one API across all of them, and its **synthetic board** lets
  you write every line of the pipeline before you touch hardware
- **Analysis:** MNE-Python for preprocessing, Braindecode for EEGNet if you go deep
- **Fallback:** NeuroSky MindWave for blink/clench triggers if everything else is claimed
