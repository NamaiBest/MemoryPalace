"use client";

import Link from "next/link";
import { EventLabel } from "@/components/ui/EventLabel";
import { IntensityDot } from "@/components/ui/IntensityDot";
import { formatConfidence, formatMomentNumber, formatTime } from "@/lib/format";
import { momentTitle } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function HeroMoment({ moment }: { moment: Moment }) {
  return (
    <div className="relative z-10 flex max-w-3xl flex-col justify-end px-6 pb-12 pt-36 md:px-12 md:pb-14 md:pt-44">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <IntensityDot value={moment.confidence} showLabel />
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

      <h1 className="mt-6 text-balance font-serif text-5xl leading-[1.12] text-fg md:text-7xl">
        {momentTitle(moment)}
      </h1>
      <p className="mt-6 max-w-lg text-base leading-8 text-fg/80">
        {moment.aiDescription ?? moment.summary}
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[12px] text-fg-dim">
        <span>{formatTime(moment.timestamp)}</span>
        <span className="text-line-strong" aria-hidden>
          /
        </span>
        <span>{formatConfidence(moment.confidence)} spike intensity</span>
      </div>

      {moment.annotation ? (
        <p className="mt-5 max-w-md border-l border-accent/30 pl-4 text-sm leading-6 text-fg-dim italic">
          {moment.annotation}
        </p>
      ) : null}

      <Link
        href={`/moment/${moment.id}`}
        className="mt-8 inline-flex w-fit items-center gap-4 rounded-xl bg-accent px-7 py-3.5 text-sm font-medium text-bg transition-colors hover:bg-fg"
      >
        <span aria-hidden>▶</span>
        Watch moment
      </Link>
    </div>
  );
}
