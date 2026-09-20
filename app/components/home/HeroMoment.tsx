"use client";

import Link from "next/link";
import { EventLabel } from "@/components/ui/EventLabel";
import { IntensityDot } from "@/components/ui/IntensityDot";
import { formatConfidence, formatMomentNumber, formatTime } from "@/lib/format";
import { momentTitle } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function HeroMoment({ moment }: { moment: Moment }) {
  return (
    <div className="relative z-10 flex max-w-3xl flex-col justify-end px-6 pb-6 pt-28 md:px-12 md:pb-7 md:pt-32">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <IntensityDot value={moment.confidence} showLabel />
        <EventLabel
          type={moment.eventType}
          confidence={moment.confidence}
          className="text-[11px] tracking-[0.24em] uppercase"
        />
        <span className="text-line-strong" aria-hidden>
          /
        </span>
        <span className="font-mono text-[11px] tracking-[0.16em] uppercase text-fg-dim">
          {formatMomentNumber(moment.sequence)}
        </span>
      </div>

      <h1 className="mt-4 line-clamp-2 text-balance font-serif text-4xl leading-[1.1] text-fg md:text-6xl">
        {momentTitle(moment)}
      </h1>
      <p className="mt-4 line-clamp-2 max-w-lg text-base leading-7 text-fg/80">
        {moment.aiDescription ?? moment.summary}
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <Link
          href={`/moment/${moment.id}`}
          className="inline-flex w-fit items-center gap-3 rounded-xl bg-accent px-6 py-3 text-sm font-medium text-bg transition-colors hover:bg-fg"
        >
          <span aria-hidden>▶</span>
          Watch moment
        </Link>
        <span className="flex flex-wrap items-center gap-x-4 font-mono text-[12px] text-fg-dim">
          <span>{formatTime(moment.timestamp)}</span>
          <span className="text-line-strong" aria-hidden>/</span>
          <span>{formatConfidence(moment.confidence)} spike intensity</span>
        </span>
      </div>

      {moment.annotation ? (
        <p className="mt-4 line-clamp-2 max-w-md border-l border-accent/30 pl-4 text-sm leading-6 text-fg-dim italic">
          {moment.annotation}
        </p>
      ) : null}

    </div>
  );
}
