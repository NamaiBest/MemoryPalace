# MemoryPalace — web interface

The browsable half of the project. It shows captured moments in a cinematic hero and
horizontal carousel, with larger cards, scroll arrows, keyboard navigation and a warm,
blurred backdrop.

On `/live`, **Demo surprise** and **Demo neural spike** request a 10- or 30-second moment.
The phone camera opens for that capture only, then closes and uploads the MP4. The backend
owns the timer, starting it after the phone acknowledges recording. No EEG calibration is
required for these manual demo triggers. Simulated signal panels live in an expandable
playground. The UI only says a moment is saved after its upload reaches the library.

**Nothing is seeded.** There is no demo data. An empty gallery means no capture has
happened, which is the honest state rather than a bug. `/debug` says which link of the
chain is down.

## Running it

```bash
npm install
npm run build
BACKEND_URL=http://127.0.0.1:8771 DEMO_TOKEN=<token> npx next start -H 0.0.0.0
```

`DEMO_TOKEN` must match the backend's. Both are read **server-side only** — the browser
never sees the token, because every backend call is proxied through `app/api/*`.

Without a backend the app still runs; it just has nothing to show.

### Use the production build, not `next dev`

On this setup `next dev` serves pages that **never hydrate**. Next's HMR WebSocket fails
its handshake:

```
WebSocket connection to 'ws://…/_next/hmr' failed:
Error during WebSocket handshake: net::ERR_INVALID_HTTP_RESPONSE
```

React starts loading, the socket retries forever, and hydration never completes. The page
looks correct because it is server-rendered, but nothing is interactive: no polling, so
captures never appear, and buttons do nothing. It presents as "the app is broken" rather
than as an error, which is what makes it expensive.

`next start` has no HMR socket, so the failure cannot occur. If you need `dev`, confirm
hydration first — load any page and check the browser console for that WebSocket error.

## Routes

```text
/                    Home — hero moment plus the carousel
/moment/[id]         One moment: media, EEG trace, annotation
/explore             Table of every moment, with filters
/live                Timed demo capture controls and optional simulated signal playground
/debug               Diagnostics: is any of this actually connected?
```

## Event types

The type is not cosmetic — it states what the system is claiming to have found.

| Type | Label | Origin | Meaning |
|---|---|---|---|
| `load` | Sustained Load | **Real detections** | Elevated cognitive load against the wearer's own calibrated baseline, held across four consecutive windows. This is what the detector actually measures. |
| `surprise` | Possible Surprise | Simulation only | Reserved for a surprise-specific detector that does not exist yet. |
| `insight` | Possible Insight | Simulation only | Reserved. The current pipeline cannot distinguish insight from load. |
| `error` | Error-related Event | Simulation only | Reserved for error-related negativity. Not implemented. |

The EEG detector produces `load`. Manual demo buttons produce `surprise` or `load` with
`demo: true` and a summary explicitly identifying the demo trigger. The footage is real
when a physical phone is connected; the event label is chosen by the tester.

If the cascade idea lands — using sustained load as a gate, then searching inside it for
short bursts — a `burst` type slots in beside `load` without rework. Adding a type means
editing `types/moment.ts`, `lib/labels.ts` (two records), `components/ui/EventLabel.tsx`
(tone plus icon), `components/explore/FilterBar.tsx`, `components/media/MediaBackdrop.tsx`
and a colour token in `app/globals.css`. TypeScript will name every site it needs.

### Confidence is a rank, not a probability

`confidence` is the detector's z-score squashed into 0–1 for **ordering**. It is not
calibrated and does not mean "83% likely to be confusion". The design deliberately ranks
rather than thresholds, because deployment class imbalance is nothing like calibration
imbalance and any emitted probability would be badly miscalibrated.

## Filtering

`/explore` filters, all defaulting to "all" and combining with AND (`lib/filters.ts`):

| Filter | Options | Notes |
|---|---|---|
| Event | all · surprise · insight · error · load | EEG events use `load`; demo triggers can also use `surprise`. |
| Confidence | high ≥80% · medium 60–79% · low <60% | Bands over the rank score above. |
| Modality | all · EEG · Video | `video` means media is attached; `eeg` means a trace is. |
| Date | all · today · last 48h | Uses Boston time, like every other timestamp. |
| Search | free text | Matches id, sequence, event label, annotation and summary. |

Intensity is the normalized detector ranking score, not a medical severity diagnosis or a
calibrated probability. The visual bands are **critical/red ≥85%**, **high/orange
70–84%**, **moderate/yellow 55–69%**, and **weak/green <55%**. Weak moments remain in the
collection intentionally: ranking lets the wearer decide what mattered without throwing
away a possibly useful memory.

Explore defaults to chronological session order and offers strongest-first ordering. Its
session line shows every filtered moment at its real position in the session; each colored
dot opens that moment. Larger rows include a still preview plus the same intensity color
used on carousel cards, the home hero, and video playback.

When Elastic is configured on the backend, that same search box becomes hybrid cognitive
memory search: Jina v5 Omni embeds video and text in a shared vector space, and Elastic fuses BM25 with dense kNN
using RRF. Event and intensity-band bounds are applied inside the Elastic query. The label
below the box states which engine answered. If Elastic is absent or
offline, the UI falls back to the local exact-text filter instead of breaking the collection.

## Memory Guard

Every page includes Memory Guard, a compact floating agent that answers over retrieved moments and
shows its actual provider. Set `MEMORYPALACE_AGENT_PROVIDER=meta` for Muse Spark 1.3 or
`grok` for Grok 4.6 before launch. Elastic remains the retrieval layer in either mode. The
UI uses an explicitly labelled grounded-catalog fallback when no model key is configured
instead of pretending an unconfigured sponsor service answered. The top-right date selector
filters the collection and scopes Memory Guard to the same Boston calendar day.

## Time

Every timestamp renders in **Boston** (`America/New_York`), pinned explicitly in
`lib/format.ts`. Two reasons: the demo is in Boston, and a fixed zone removes a hydration
hazard where the server and the browser format differently on first paint.

The backend stores UTC; conversion happens only at display.

## Where the data comes from

```text
phone ──upload──> backend ──> durable catalog + media library
                              ├─/api/moments──> MomentsProvider ──> pages
                              └─/api/media/… ──> <img> and <video>
```

`MomentsProvider` polls `/api/moments` every 5 s and merges by id, so a capture appears
shortly after it is uploaded without a refresh. Real captures sort above anything else.
The backend reloads the durable catalog on restart, keeps its previous generation as a
backup, and imports older run media without deleting those originals.

`/api/media/[name]` supports byte ranges (`206`), which `<video>` requires in order to seek
or even determine duration.

## Stack

Next.js 16 (App Router), React 19, TypeScript, Tailwind 4. No charting or icon library —
the EEG traces are hand-drawn to canvas.

## Layout

```text
app/                 routes, including api/ proxies to the backend
components/          UI by feature (home, moment, explore, live, debug)
context/             MomentsProvider — the in-memory moment list
data/media.ts        placeholder scene art for simulated views
lib/backend.ts       server-only backend client; holds the token
lib/integrations.ts  the boundary where live data enters
types/moment.ts      the Moment model
```
