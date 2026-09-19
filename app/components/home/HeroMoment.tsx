"use client";

import Link from "next/link";
import { EventLabel } from "@/components/ui/EventLabel";
import { formatConfidence, formatMomentNumber, formatTime } from "@/lib/format";
import type { Moment } from "@/types/moment";

export function HeroMoment({ moment }: { moment: Moment }) {
  return (
    <div className="relative z-10 flex max-w-2xl flex-col justify-end px-5 pb-8 pt-24 md:px-8 md:pb-10">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <EventLabel
          type={moment.eventType}
          className="text-[11px] tracking-[0.24em] uppercase"
        />
        <span className="text-line-strong" aria-hidden>
          /
        </span>
        <span className="font-mono text-[11px] tracking-[0.16em] uppercase text-fg-dim">
          {formatMomentNumber(moment.sequence)}
        </span>
      </div>

      <h1 className="mt-5 max-w-xl text-balance font-serif text-[1.75rem] leading-[1.15] text-fg md:text-[2.75rem]">
        {moment.summary}
      </h1>

      <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[12px] text-fg-dim">
        <span>{formatTime(moment.timestamp)}</span>
        <span className="text-line-strong" aria-hidden>
          /
        </span>
        <span>{formatConfidence(moment.confidence)} Event Confidence</span>
      </div>

      {moment.annotation ? (
        <p className="mt-5 max-w-md border-l border-accent/30 pl-4 text-sm leading-6 text-fg-dim italic">
          {moment.annotation}
        </p>
      ) : null}

      <Link
        href={`/moment/${moment.id}`}
        className="mt-8 inline-flex w-fit items-center gap-3 border border-accent/50 px-5 py-2.5 text-[11px] tracking-[0.22em] uppercase text-accent transition-colors hover:bg-accent hover:text-bg"
      >
        View Moment
        <span aria-hidden>→</span>
      </Link>
    </div>
  );
}
