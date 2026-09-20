import { ModalityPills } from "@/components/ui/ModalityPills";
import { IntensityDot } from "@/components/ui/IntensityDot";
import {
  formatConfidence,
  formatContextWindow,
  formatDate,
  formatMomentNumber,
  formatTimeWithSeconds,
} from "@/lib/format";
import { momentTitle, STATUS_LABELS } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function MomentMetadata({ moment }: { moment: Moment }) {
  return (
    <section className="grid gap-8 border-b border-line py-8 md:grid-cols-[1.3fr_0.7fr]">
      <div>
        <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">
          {formatMomentNumber(moment.sequence)}
        </p>
        <h1 className="mt-3 font-serif text-3xl md:text-4xl">
          {momentTitle(moment)}
        </h1>
        <Description moment={moment} />
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 text-sm md:grid-cols-1">
        <div>
          <dt className="text-[10px] tracking-[0.18em] uppercase text-fg-mute">
            Timestamp
          </dt>
          <dd className="mt-1 font-mono text-fg">
            {formatTimeWithSeconds(moment.timestamp)}
            <span className="mt-1 block text-fg-dim">{formatDate(moment.timestamp)}</span>
          </dd>
        </div>
        <div>
          <dt className="text-[10px] tracking-[0.18em] uppercase text-fg-mute">
            Spike Intensity
          </dt>
          <dd className="mt-1 flex items-center gap-2 font-mono text-fg">
            <IntensityDot value={moment.confidence} />
            {formatConfidence(moment.confidence)}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] tracking-[0.18em] uppercase text-fg-mute">
            Captured context
          </dt>
          <dd className="mt-1 font-mono text-[13px] text-fg">
            {formatContextWindow(moment.contextWindow.start, moment.contextWindow.end)}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] tracking-[0.18em] uppercase text-fg-mute">
            Status
          </dt>
          <dd className="mt-1 text-fg">{STATUS_LABELS[moment.status]}</dd>
        </div>
        <div>
          <dt className="mb-2 text-[10px] tracking-[0.18em] uppercase text-fg-mute">
            Modalities
          </dt>
          <dd>
            <ModalityPills moment={moment} />
          </dd>
        </div>
      </dl>
    </section>
  );
}

/**
 * The description has three honest states, and they must not look alike.
 *
 * While extraction or analysis is still pending the Meta call is in flight — that can
 * take a while — so show that it is coming rather than quietly substituting the generic
 * summary, which reads as "the writeup never happened". If analysis failed, say so and
 * show the error, because a fallback sentence presented as a description is a lie by
 * omission. Only when it genuinely completed does the AI text stand on its own. The
 * provider polls every few seconds, so a pending state fills in without a refresh.
 */
function Description({ moment }: { moment: Moment }) {
  const p = moment.processing;
  const pending = p?.extraction === "pending" || p?.analysis === "pending";
  const failed = moment.vision?.status === "failed" || p?.analysis === "failed";

  if (pending) {
    return (
      <div className="mt-4 max-w-2xl" role="status" aria-live="polite">
        <p className="flex items-center gap-2 text-[11px] tracking-[0.18em] uppercase text-accent">
          <span className="processing-ring h-3.5 w-3.5" aria-hidden />
          {p?.extraction === "pending" ? "Extracting the clip…" : "Meta is describing this moment…"}
        </p>
        <p className="mt-2 text-base leading-7 text-fg-mute">{moment.summary}</p>
        <p className="mt-2 text-[12px] leading-5 text-fg-mute">
          The full description fills in here on its own — typically well under a minute,
          occasionally longer for a busy clip. No need to refresh.
        </p>
      </div>
    );
  }

  if (p?.analysis === "not_configured") {
    return (
      <div className="mt-4 max-w-2xl">
        <p className="text-base leading-7 text-fg-dim">{moment.summary}</p>
        <p className="mt-3 text-[12px] leading-5 text-fg-mute">
          No AI description: the backend was started without <code className="font-mono">MODEL_API_KEY</code>.
        </p>
      </div>
    );
  }

  if (failed) {
    return (
      <div className="mt-4 max-w-2xl">
        <p className="text-base leading-7 text-fg-dim">{moment.summary}</p>
        <p className="mt-3 border-l-2 border-error/60 pl-3 text-[12px] leading-5 text-fg-dim">
          AI description unavailable
          {moment.vision?.error ? `: ${moment.vision.error}` : "."}
        </p>
      </div>
    );
  }

  return (
    <p className="mt-4 max-w-2xl text-base leading-7 text-fg-dim">
      {moment.aiDescription ?? moment.summary}
    </p>
  );
}
