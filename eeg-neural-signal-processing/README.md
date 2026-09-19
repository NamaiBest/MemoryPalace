# EEG Neural Signal Processing - HackMIT Idea

## What we've achieved so far (plain summary)

We started with two ideas: (1) unlock/authenticate a person using their brainwaves
instead of a fingerprint, and (2) a wearable camera that acts like a dash cam for people
with dementia, always keeping the last ~2 minutes in a buffer and saving it when
something happens. The goal was to figure out, with real evidence, which of these is
worth building at HackMIT.

**Research, done:** wrote up how EEG sensors actually work, checked every idea against
HackMIT's real hardware list, and found the "glasses as electrode clamp" idea is doable
but only for certain signals, not others.

**Data, downloaded:** pulled ~1.8 GB of real public EEG recordings from 129 different
people (PhysioNet's auditory-biometric set and the Motor Movement/Imagery database), not
just cited from papers. Everything below was measured on this machine, not looked up.

**Idea 1 (brainwave unlock), tested and mostly ruled out for a hackathon demo:** the
signal to identify a person is real (82% accuracy across 109 people), but it falls apart
the moment anything changes: closing your eyes between enrollment and test nearly triples
the error rate, and switching from a 64-electrode lab cap to 8 consumer electrodes costs
36 points of accuracy. This is a real research problem, but not a three-minute demo.

**Idea 2 (dash cam trigger), tested and it works:** built and tested a way to detect a
brain-state change and decide when to save the buffer. With a simple "require several
seconds in a row before triggering" rule, it hits 100% detection with about 1.5 false
saves per hour, using only the two electrode positions a glasses frame can actually
reach. The ~28 seconds it takes to be sure is free, because the buffer already has the
last 2 minutes saved anyway.

**Bonus, tested what else EEG can tell us beyond a simple trigger:**
- What state you're in (resting, listening, etc.) - works reasonably well
- What you're actually hearing/perceiving - does not work, no signal at all
- Who you are (the biometric idea) - works but unreliable, as above
- A deliberate brain "command" (imagining moving your hand) - works, but only for
  about 1 in 3 people, and needs electrodes glasses cannot reach

**Current recommendation:** build idea 2 (the dash cam) as the main HackMIT project. Use
the brainwave-identity code only as a small side feature (checking "is this device on the
right person's head"), not as the main pitch, since it is not reliable enough on its own.

**Not built yet:** no actual recorder/hardware code exists yet. Everything so far is
research and data analysis to de-risk the plan before touching real hardware at the
event.

## Note: this matches a concern the team already flagged

The team's own HackMIT Brainstorm doc already identified this exact problem for the
BrainPrint idea: "P300 prefers central/parietal electrodes (Pz) that Muse lacks." The
measurements in this folder are the quantified version of that same worry - Pz-style
central/parietal sites outperform the frontal/temporal sites any headband or glasses
frame can reach, on every dataset tested here. It is the same limitation, now with
numbers attached.

## Next steps

- Build the real ring-buffer camera recorder with the tested trigger logic, using a
  laptop webcam and a simulated EEG feed, so it already works before we touch HackMIT's
  hardware desk.
- Request access to the BED dataset (currently gated, not open like the others) to get a
  true "different day" accuracy number for the biometric side feature.
- Look into SSVEP (flicker-based brain commands) as a better "deliberate signal" channel
  for glasses, since imagined-movement commands need electrodes a frame cannot reach.

---

## Documents in this folder

| Doc | What it covers |
|---|---|
| [PLAN.md](PLAN.md) | The detailed build plan, including the uniqueness question and a 36-hour HackMIT schedule. |
| [EEG-SENSORS-AND-DATASETS.md](EEG-SENSORS-AND-DATASETS.md) | How EEG sensors actually work (channels vs. bit depth vs. sample rate), plus every open dataset worth downloading. |
| [GLASSES-PLUS-EEG-IDEAS.md](GLASSES-PLUS-EEG-IDEAS.md) | The glasses-as-electrode-carrier idea, plus 9 other things this setup can do. |
| [HACKMIT-HARDWARE-REALITY-CHECK.md](HACKMIT-HARDWARE-REALITY-CHECK.md) | What HackMIT actually stocks, what's usable, and what will silently kill a build. |
| [RESULTS.md](RESULTS.md) | All the measured numbers: biometrics, the trigger, and what else can be decoded. This is the evidence behind the summary above. |

## Code and data in this folder

- `src/` - all the Python: downloader, feature extraction, the trigger, the decoding
  experiments.
- `results/` - the JSON output of every experiment in RESULTS.md.
- `data/` - the downloaded EEG datasets (~1.8 GB). **Not tracked by git** - see
  `.gitignore`. Regenerate with `src/download.py` (see RESULTS.md's "Reproducing"
  section).
- `.venv/` - local Python environment. Not tracked by git.

## The two ideas, in one line each

**A. Neural signature validation** - authenticate a person from their EEG instead of a
fingerprint. The appeal: a fingerprint can be lifted off a glass and a face can be
photographed, and both still work on a corpse. An EEG needs a living, conscious,
cooperating brain.

**Why this is not buildable as full authentication on glasses: we simply do not have
enough electrodes, and getting more is not free.** A real EEG cap uses 32-64+
electrodes spread across the whole scalp, because different identity-relevant signals
(P300, alpha rhythm, the central/parietal sites the literature says matter most) live in
different places. A glasses frame only has room for electrodes on the two temple arms
and maybe the bridge, roughly 2-4 contact points, all in the frontal/temporal region.
Measured directly on our own data (§6 and §8 in [RESULTS.md](RESULTS.md)): the two
positions a frame can reach were the *worst* pair in a 4-channel montage, and going
from 64 electrodes to 8 cost 36 points of accuracy. This is not a software problem a
better model fixes - the information genuinely is not present in only a couple of
frontal contacts.

Real research glasses that add more EEG electrodes confirm the tradeoff: GAPses (ETH
Zurich, IEEE TBCAS 2024) fits **8 dry brush-style electrodes** along the temple arms and
gets 98.9% biometric sensitivity, but needs a noticeably thicker frame and a dedicated
low-power chip to process 8 channels on-device
([paper](https://pubmed.ncbi.nlm.nih.gov/39388333/)). e-Glass (Nature Scientific
Reports, 2025) uses spring-loaded piston electrodes for a solid skin contact and
validates well against clinical-grade EEG, but the electrode housings visibly bulge off
the frame ([open-access paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12698764/)).
**More electrodes on glasses is possible, but it stops looking like glasses.** Two
electrodes that stay genuinely glasses-shaped is roughly what we tested, and roughly
what the numbers above are.

**B. Retrospective capture ("dash cam for humans")** - a wearer-mounted camera keeps a
rolling buffer of the last ~2 minutes. Nothing is stored until a physiological trigger
fires, at which point that buffer is committed to disk. Built for dementia, epilepsy, and
memory impairment.

## On sustainability

Do not force an environmental angle - judges see through it. Two angles are legitimate:

- **Care-system sustainability (lead with this).** 57M people live with dementia, a
  number projected to hit 139M by 2050, with ~18.4 billion hours of unpaid care given
  annually and US$1.3T in societal cost. Tools that let one caregiver cover more people
  without more hours is a sustainability argument that is simply true. This is SDG 3 and
  SDG 10.
- **Measured compute/storage reduction (secondary, only if you measure it).** Event-gated
  capture stores ~2 minutes instead of ~16 hours per day, roughly a 99.8% reduction in
  bytes written and inference time. Put the actual measured number on a slide, or say
  nothing.
