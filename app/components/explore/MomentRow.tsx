"use client";

/* eslint-disable @next/next/no-img-element */

import { useRouter } from "next/navigation";
import { EventIcon } from "@/components/ui/EventLabel";
import { IntensityDot } from "@/components/ui/IntensityDot";
import { formatConfidence, formatDateTime } from "@/lib/format";
import { intensityMeta } from "@/lib/intensity";
import { eventLabel, formatModalities, momentTitle, STATUS_LABELS } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function MomentRow({ moment }: { moment: Moment }) {
  const router = useRouter();
  const intensity = intensityMeta(moment.confidence);

  return (
    <tr
      tabIndex={0}
      onClick={() => router.push(`/moment/${moment.id}`)}
      onKeyDown={(event) => {
        if (event.key === "Enter") router.push(`/moment/${moment.id}`);
      }}
      className="group cursor-pointer border-b border-line text-sm transition-colors hover:bg-fg/[0.045] focus-visible:bg-fg/[0.05] focus-visible:outline-none"
    >
      <td className="py-4 pr-6">
        <div className="flex min-w-[360px] items-center gap-4">
          <div className="relative h-[72px] w-28 shrink-0 overflow-hidden rounded-lg border border-white/10 bg-bg-panel">
            {moment.media.thumbnailUrl ? (
              <img
                src={moment.media.thumbnailUrl}
                alt=""
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-fg-mute">▶</div>
            )}
            <IntensityDot value={moment.confidence} className="absolute left-2 top-2 !p-1.5" />
          </div>
          <div className="min-w-0">
            <span className="inline-flex items-center gap-2.5 font-mono text-[12px] text-fg">
              <EventIcon type={moment.eventType} />
              {momentTitle(moment)}
            </span>
            <p className="mt-1.5 max-w-sm truncate text-[13px] text-fg-dim">
              {moment.aiDescription ?? moment.summary}
            </p>
          </div>
        </div>
      </td>
      <td className="whitespace-nowrap py-4 pr-6 text-fg-dim">
        {formatDateTime(moment.timestamp)}
      </td>
      <td className="py-4 pr-6">{eventLabel(moment.eventType, moment.confidence)}</td>
      <td className="whitespace-nowrap py-4 pr-6">
        <span className="inline-flex items-center gap-2 font-mono text-[12px]">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: intensity.color }} />
          <span>{intensity.label}</span>
          <span className="text-fg-mute">{formatConfidence(moment.confidence)}</span>
        </span>
      </td>
      <td className="hidden py-4 pr-6 text-fg-dim md:table-cell">
        {formatModalities(moment)}
      </td>
      <td className="hidden whitespace-nowrap py-4 text-fg-mute lg:table-cell">
        {STATUS_LABELS[moment.status]}
      </td>
    </tr>
  );
}
