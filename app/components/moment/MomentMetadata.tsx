import { ModalityPills } from "@/components/ui/ModalityPills";
import {
  formatConfidence,
  formatContextWindow,
  formatDate,
  formatMomentNumber,
  formatTimeWithSeconds,
} from "@/lib/format";
import { eventLabel, STATUS_LABELS } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function MomentMetadata({ moment }: { moment: Moment }) {
  return (
    <section className="grid gap-8 border-b border-line py-8 md:grid-cols-[1.3fr_0.7fr]">
      <div>
        <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">
          {formatMomentNumber(moment.sequence)}
        </p>
        <h1 className="mt-3 font-serif text-3xl md:text-4xl">
          {eventLabel(moment.eventType)}
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-fg-dim">
          {moment.summary}
        </p>
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
            Event Confidence
          </dt>
          <dd className="mt-1 font-mono text-fg">
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
