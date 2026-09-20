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
