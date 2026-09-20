# Sponsor Challenge Fulfillment

This is the shared, evidence-first record of how MemoryPalace uses sponsor technology.
Each section separates what is running from what is future work so the demo and submission
do not overclaim. The live verification on 2026-09-19 preserved, enriched, and indexed all
12 historical moments.

## Common product architecture and pitch policy

The product agent is always named **Memory Guard**. Sponsor services have separate jobs:

| Layer | Fixed or selectable? | Responsibility |
|---|---|---|
| Elastic | Fixed when configured | BM25 + vector retrieval, RRF ranking, and EEG intensity filters |
| Voice input | Meta when configured | Muse Voice Transcribe converts a push-to-talk turn into the question Memory Guard answers |
| Memory Guard LLM | Selected at launch | Meta Muse Spark 1.3 **or** Grok 4.6 reasons over retrieved moments |
| Voice output | Device native | Browser speech synthesis reads the grounded answer aloud; this is not presented as a Meta TTS API |

This avoids misleading overlap. In a Meta launch, Muse Spark genuinely generates Memory
Guard's answers. In a Grok launch, Grok genuinely does. Elastic remains the search system in
both launches. The active provider and model are
shown on the homepage rather than hidden in configuration.

## Elastic — Multimodal Episodic Memory and Cognitive Search

### Sponsor narrative we are fulfilling

MemoryPalace uses Elastic as the retrieval engine for a new kind of searchable record: a
timeline of moments selected by a physiological signal and paired with first-person video.
Elastic is not a passive JSON backup. It turns noisy cognitive events into a ranked memory
index that can answer natural questions while retaining structured signal filters.

The product story is:

```text
EEG spike + phone video
        ↓
durable cognitive moment
        ↓
Meta Muse Spark semantic title + grounded scene description
        ↓
Meta web grounding for supported public event context
        ↓
Jina v5 Omni video/text embedding through Elastic Inference Service
        ↓
BM25 keyword retrieval + dense kNN vector retrieval
        ↓
Reciprocal Rank Fusion (RRF)
        ↓
time, event, and spike-intensity filters
        ↓
clickable return to the original moment
```

### What we implemented

| Elastic capability | How MemoryPalace uses it | Repository evidence |
|---|---|---|
| **Elastic Cloud Serverless Vector Database** | Stores a searchable document for every captured cognitive moment in `memorypalace-multimodal-moments`. Source video stays in the durable media library; Elastic stores its URI, metadata, and searchable vector. | `hardware-demo/eegdemo/elastic_store.py` |
| **Elastic Inference Service** | Uses the preconfigured `.jina-embeddings-v5-omni-small` endpoint to place short videos and text queries in the same 1024-dimensional space. No separate Jina credential is exposed to the browser or phone. | `ElasticStore.embed_video()` and `ElasticStore.embed_text()` |
| **Semantic metadata** | Indexes Meta's grounded title, description, keywords, and topics alongside structured EEG fields. BM25 can match visible scene details while dense retrieval handles paraphrases. | `hardware-demo/eegdemo/vision.py`, `Library._enrich_meta()`, and `ElasticStore.index_moment()` |
| **Pre-indexed event context** | Stores verified public context such as `HackMIT` in the same stable moment document before query time. The operator hint is retained only as provenance; Elastic searches the grounded title, description, keywords, and topics rather than assuming the hint is true. | `MetaVideoDescriber._ground_semantics()`, `ElasticStore.searchable_text()`, and `vision` metadata |
| **Text-to-video vector search** | Sends short MP4 bytes as base64 video input, indexes the returned cosine-similarity vector, and embeds natural-language queries with the same model for kNN retrieval. | `ElasticStore.index_moment()` and `ElasticStore.search()` |
| **BM25 + RRF hybrid search** | Runs conventional multi-field keyword search alongside kNN and merges their rankings with reciprocal rank fusion. Exact terms and semantic intent can both win. | `retriever.rrf` body in `ElasticStore.search()` |
| **Structured filtering** | Applies event type and lower/upper spike-intensity bounds inside both the keyword and vector branches. The UI exposes critical/red, high/orange, moderate/yellow, and weak/green bands. | `GET /search`, `app/app/api/search/route.ts`, and `ExplorePage.tsx` |
| **Search experience** | `/explore` supports questions such as “when was I startled while reading?”, reports when Elastic answered, draws each result on the session timeline, and opens the original captured video. | `app/components/explore/` |
| **Resilient ingestion** | Local capture is acknowledged before sponsor enrichment. Elastic indexing runs off the upload path, failures are logged without losing the video, and every durable local moment is re-indexed when Elastic reconnects. | `hardware-demo/eegdemo/library.py` |

### Why this is meaningfully Elastic

A plain database lookup could filter timestamps, and a generic vector store could return
similar text. This implementation needs both. A user might remember an exact term from the
scene, describe the scene indirectly, or ask only for strong physiological reactions. RRF
combines lexical and semantic evidence, while Elasticsearch range and term filters preserve
the biological context. The result is episodic recall, not a chatbot pasted over a document
collection.

### Live demo path

1. Pair the Meta-style Android demo app. The phone connects with its camera off.
2. Capture a 10- or 30-second moment from `/live`.
3. The MP4 is finalized, uploaded, and written to the durable memory catalog.
4. Meta Muse Spark generates factual media metadata, then optionally verifies relevant
   public proper nouns using web search and the configured event hint.
5. The video is embedded by Jina v5 Omni and the complete document is indexed into Elastic.
6. Open `/explore`, enter a natural-language memory query, and optionally choose an
   intensity range, date, or session.
7. Show `ELASTIC · JINA V5 OMNI · HYBRID RRF`, then click the colored timeline point to replay
   the source moment.

### Persistence and privacy boundary

- `hardware-demo/library/moments.json` and its atomic backup are the durable source of
  truth across backend, frontend, and APK updates.
- Media is copied into `hardware-demo/library/`; legacy originals under `runs/` are never
  moved or deleted.
- On startup, older uncatalogued captures are imported idempotently. The current migration
  preserved all 12 historical MP4s and exposed all 12 through `/api/moments`.
- The Elastic API key stays server-side. It is never compiled into Android, returned by
  `/status`, committed, or sent to the browser.
- The intensity value is a normalized detector ranking score, not a medical diagnosis or a
  calibrated probability.

### Configuration

```bash
export ELASTICSEARCH_URL="https://my-elasticsearch-project-f50785.es.us-central1.gcp.elastic.cloud:443"
export ELASTIC_API_KEY="<project API key>"
python3 hardware-demo/run.py serve \
  --source synthetic --recorder phone --host 0.0.0.0
```

The application needs `manage_inference` at cluster scope and `create_index`, `index`, and
`read` only on `memorypalace-multimodal-moments`. This supports index setup and search
without granting access to unrelated indices.

### Verification

- 41 Python tests pass, covering catalog restart survival, non-destructive legacy import,
  Meta video/poster understanding, launch-selected agent routing, Jina video ingestion,
  RRF queries, conversation history, and Meta voice request handling.
- Frontend lint, TypeScript, and the Next.js production build pass.
- `/status` exposes readiness and index names but never credentials.
- Without Elastic credentials, search visibly falls back to local text matching; camera
  capture and the durable gallery remain operational.
- Live cloud verification returned 12 documents for 12 durable memories; every catalog
  item reports Meta analysis and Elastic indexing complete. A `laptop keyboard` query
  returned the keyboard clip first through `elastic-rrf-jina-v5-omni`.
- The auditorium migration used Meta web search to resolve HackMIT from the full video,
  sponsor signage, transcript, timestamp, and configured event clue, then updated the same
  Elastic documents. No media or historical moment was replaced.

### Honest remaining boundary

Elastic Workflows and Agent Builder remain future extensions in `DOCS_sponsor/elastic`;
they are not presented as completed work. The working implementation uses Elastic Cloud,
Elastic Inference Service, Jina v5 Omni, BM25, dense kNN, RRF, and structured range filters.

Meta Muse Spark now analyzes the stored MP4 directly when it is 6 MB or smaller. For larger
clips it analyzes the extracted poster image so network-size failures cannot block the
library. The recorded `vision.source` value keeps that distinction explicit. Descriptions
are conservative scene metadata, not emotion, identity, medical, or intent inference.
Public context is a second pass so a web result cannot override what the private clip
actually contains. Search provenance is stored under `vision.webSearchUsed` and
`vision.webSources`; failures leave the original media description intact.

Official implementation references:

- [Elastic Inference Service and Jina models](https://www.elastic.co/docs/explore-analyze/elastic-inference/eis)
- [Elastic multimodal search](https://www.elastic.co/docs/solutions/search/multimodal-search)
- [kNN search in Elasticsearch](https://www.elastic.co/docs/solutions/search/vector/knn)
- [Vector search and RRF](https://www.elastic.co/docs/solutions/search/vector)
- [Serverless project API keys](https://www.elastic.co/docs/current/serverless/api-keys)

## Meta / Grok — Memory Guard's launch-selected reasoning provider

Memory Guard follows every page and uses the same moment context in either launch mode.
`MEMORYPALACE_AGENT_PROVIDER=meta` selects Meta's Responses API with `muse-spark-1.3` and
`MODEL_API_KEY`; `grok` selects xAI's Responses API with `grok-4.6` and `XAI_API_KEY`.
`scripts/start-memorypalace.sh` validates the matching key before starting the stack.

The window is mounted globally, so it remains available on Home, Explore, Live, Diagnostics,
and moment detail pages. A shared top-right date selector scopes both the displayed catalog
and Memory Guard retrieval to the same Boston calendar day. Without a model key, the window
uses a clearly labelled local grounded-catalog answer with moment citations; it never labels
that fallback as Meta or Grok inference.

The same window now supports typed and spoken turns. Tapping the voice control records up to
30 seconds, sends the audio server-side to Meta Muse Voice Transcribe, retrieves matching
moments from Elastic, and asks the selected Memory Guard model with the preceding conversation.
The transcript appears as the user's message, the cited moment buttons still open the original
video, and the answer is spoken aloud. Raw microphone audio is ephemeral and is not persisted.
Because Meta's documented voice endpoint is transcription-only, output speech uses browser or
OS speech synthesis and is labelled `Device speech synthesis` in the runtime provenance.

This provider selection affects the agentic overview only. It does not relabel Elastic search
as an LLM feature.

The Meta product path and constraints are documented in `DOCS_sponsor/meta`. The phone app
uses `Pair Meta glasses` to open the real Meta AI companion app, then returns to a clearly
labelled simulated connection while the phone remains the working camera. The UI names its
actual authenticated JSON start/stop/ack bridge. For a physical-glasses build, the documented
upgrade is Meta Wearables Device Access Toolkit v0.9 registration, permission, device-session,
and camera-stream APIs rather than an invented REST recording command. The Meta adapters were
verified live with Muse Spark on 2026-09-19. Provider availability and credits remain external
runtime dependencies, so durable capture and local browsing continue to work during an outage.

Official references:

- [Meta Model API overview](https://dev.meta.ai/docs/overview)
- [Meta Responses API](https://dev.meta.ai/docs/protocols/responses)
- [Meta speech-to-text guide](https://dev.meta.ai/docs/speech-to-text)
- [Muse Voice Transcribe API](https://dev.meta.ai/docs/api-reference/voice/transcribe)
- [Meta Wearables Android integration](https://wearables.developer.meta.com/docs/develop/dat/build-integration-android/)
- [Official Device Access Toolkit Android repository](https://github.com/facebook/meta-wearables-dat-android)
- [xAI Grok 4.6](https://docs.x.ai/developers/grok-4-6)

---

## VoloRidge — Public-data challenge: finding signal, and proving where there is none

### Sponsor narrative we are fulfilling

> "Build something interesting using one or more public datasets."

MemoryPalace decides when a moment is worth capturing from a physiological signal. The
question underneath the product is empirical and answerable on public data: **can scalp EEG
mark cognitive state changes well enough to trigger a camera, and how would you know you
were not fooling yourself?**

Our answer is in [`eeg-state-detection/`](eeg-state-detection/README.md). It is one dataset,
five participants, fifteen sessions, evaluated walk-forward with every model frozen before
scoring, and benchmarked against two purpose-built null distributions. The interesting part
is not only that we found signal. It is that **the same method proved that our most
promising-looking result was noise**, and we kept the record.

### The dataset

[Shin et al. 2018, dataset A](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/)
([Scientific Data](https://doi.org/10.1038/sdata.2018.3)), an open EEG/NIRS corpus.

| | |
|---|---|
| Signal | 28 EEG channels + 2 EOG, 1000 Hz, analysed at 200 Hz |
| Task | n-back working memory, 0-/2-/3-back, nine blocks per session |
| Used here | VP002 to VP006, three sessions each = 15 sessions |
| Ground truth | The experiment's own block and stimulus markers, never recoded |
| Licence | Public, citable, redistributed by the authors |

Recordings are not committed (about 120 MB per participant). `scripts/fetch_shin.py`
downloads a participant and verifies every file against the archive's CRC.

### What we did

| Step | Decision |
|---|---|
| Preprocess | Eye regression fitted on a separate pre-task segment, then frozen. Fixed amplitude and step limits reject artifact windows. |
| Features | Log band power in theta, alpha and beta across 28 channels, 2 s windows, every 0.25 s |
| Model | Standardized, class-balanced logistic regression, task versus rest. Regularization chosen over **whole calibration blocks**, never over shuffled neighbouring windows. |
| Temporal | Causal exponential moving average of the margin, half-life selected on calibration data only |
| Split | Per session: first six blocks calibrate, last three are scored. Models saved and SHA-256 hashed **before** any held-out block is touched. |
| Transfer | None. Weights never cross a session or a person. |

### Two nulls, because a good-looking score is not a result

**Circular time-shift null (state detection).** The intact out-of-sample score trace is
shifted against the labels 2000 times per session. Shifting preserves autocorrelation, which
shuffling destroys; overlapping EEG windows are not independent samples, so a shuffle-based
p-value would be fiction. The null intervals reach 0.8 AUROC because a task period covers
most of an excerpt. We report that width rather than hiding it.

**Random-flag null (brief events).** Flags placed at random on the same valid grid, under the
same budget of five per block, the same 1.5 s separation and the same ±0.5 s matching
tolerance. Chance here is not zero: five random flags match about 3 of 36 targets.

### Results

**Sustained state detection works, and varies by person.** Out-of-sample AUROC, task versus
rest, against the shift null:

| Participant | Mean AUROC | Per session | Sessions with p ≤ 0.05 | Eye-only control |
|---|---:|---|---:|---:|
| VP002 | 0.925 | 0.904 / 0.898 / 0.972 | 3/3 | 0.883 |
| VP003 | 0.800 | 0.716 / 0.930 / 0.754 | 1/3 | 0.848 |
| VP004 | 0.652 | 0.809 / 0.605 / 0.543 | 1/3 | 0.522 |
| VP005 | 0.888 | 0.726 / 1.000 / 0.938 | 2/3 | 0.559 |
| VP006 | 0.669 | 0.658 / 0.480 / 0.871 | 1/3 | not run |

**8 of 15 sessions beat the null at p ≤ 0.05**, and 14 of 15 sit above chance.

**Brief evoked events do not work, and the null is what proved it.** Five detectors, four
participants, all scored against random placement:

| Detector | Participant | Targets matched | Random mean [95%] | p(random ≥ observed) |
|---|---|---:|---:|---:|
| Mean-amplitude bins | VP001 | 4/36 | 3.00 [0, 6] | 0.35 |
| xDAWN covariance | VP001 | 6/36 | 3.00 [0, 6] | 0.07 |
| Mean-amplitude bins | VP002 | 3/36 | 3.15 [0, 6] | 0.63 |
| Mean-amplitude bins | VP005 | 2/36 | 3.63 [1, 7] | 0.90 |
| **Zigzag persistent homology** | VP005 | **6/36** | 3.63 [1, 7] | **0.13** |
| Combined | VP005 | 3/36 | 3.63 [1, 7] | 0.72 |

The zigzag row is the point. Six matches against a two-match baseline reads as a threefold
improvement, and it is inside the range of randomly thrown darts. Without the null we would
have shipped it.

We then pre-registered a rescue attempt in
[`background_negatives_protocol.md`](eeg-state-detection/background_negatives_protocol.md),
froze it, and ran it once on VP006, a participant no analysis had touched. Adding
calibration-only background negatives moved matches from 0/36 to 2/36 with p = 0.83 against
the null. The prespecified adoption rule failed on its chance condition, so **nothing was
adopted**, and the protocol, the run and the refusal are all in the repository.

### Why this is meaningfully a public-data result

The dataset is unmodified and the labels are the experimenters', not ours. Every claim is
reproducible from the committed models with one command. The methodology is the deliverable
as much as the numbers: frozen protocols written before each fresh participant, a holdout
participant consumed exactly once, nulls matched to the evaluation rules rather than to
textbook assumptions, and adversarial controls we ran against ourselves.

The eye-only control is the clearest example. We ran the identical pipeline on the two EOG
channels, which carry no cortical signal. On VP002 and VP003 the eyes alone reach 0.88 and
0.85, close to the EEG detector, so part of that signal may be ocular even after eye
regression. On VP005 the EEG detector reaches 0.89 while the eyes reach 0.56. We publish
both rather than only the flattering one.

This also decided the product. The detector that survived is a **sustained-state** detector,
which is why MemoryPalace captures forward on a persistence filter instead of buffering
backward for an instantaneous spike.

### Verification

```bash
cd eeg-state-detection
python -m venv .venv && .venv/bin/pip install -e '.[test,real]'
.venv/bin/python -m pytest -q                                   # 79 tests
.venv/bin/python scripts/fetch_shin.py --subject 2 --out data/shin2018/VP002
.venv/bin/python -m eeg_moments backtest --out outputs/backtest_state_reproduction
```

| Artifact | Path |
|---|---|
| Walk-forward figures, null, interpretation | `eeg-state-detection/outputs/backtest_state/` |
| Random-flag null for brief events | `eeg-state-detection/outputs/burst_diagnostic_dev/` |
| Frozen VP006 comparison and its refusal | `eeg-state-detection/outputs/background_vp006/` |
| Protocols written before each run | `eeg-state-detection/*_protocol.md` |
| Full chronological research log | `eeg-state-detection/RESEARCH_LOG.md` |

Verification built into the code, not just asserted: fitted-state and file hashes checked
before and after inference, held-out blocks tested against every model's training hashes,
no-future-leakage tests on the temporal recursion, and byte-for-byte reproduction of earlier
event exports.

### Honest remaining boundary

- **The label is task versus rest**, a proxy for a cognitive state change. It is not
  confusion, insight, or focus, and we never call it that.
- **Ocular contribution is not isolated** on VP002 and VP003, as the eye-only control shows.
- **Two participants are weak.** VP004 averages 0.652 and VP006 0.669; on VP006 the detector
  flags 28 of 72 seconds of labeled rest, so its intervals are not usable as-is.
- **72 seconds of labeled rest per participant** is too little to estimate a false-alarm rate
  per hour. The trigger's operating-point evidence is in `confusion-detector/` instead.
- **Session-specific weights.** Each session is calibrated on its own first six blocks;
  nothing here shows a model that transfers between people.
- **These are public participants**, unrelated to anyone filmed by the phone in the demo. A
  shared playback clock is a presentation convention, never physiological synchronisation.
