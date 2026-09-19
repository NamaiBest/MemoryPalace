"use client";

import { cn } from "@/lib/cn";
import { formatMomentNumber, formatTime } from "@/lib/format";
import { eventLabel } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function MomentCard({
  moment,
  selected,
  onSelect,
}: {
  moment: Moment;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(moment.id)}
      aria-pressed={selected}
      className={cn(
        "group relative h-[8rem] w-[14rem] shrink-0 overflow-hidden text-left transition-all duration-300 md:h-[9.5rem] md:w-[17rem]",
        selected
          ? "ring-1 ring-accent brightness-100"
          : "brightness-[0.72] hover:brightness-95",
      )}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={moment.media.thumbnailUrl}
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 p-2.5">
        <p className="font-mono text-[10px] tracking-[0.14em] text-accent">
          {formatMomentNumber(moment.sequence).replace("Moment ", "")}
        </p>
        <p className="mt-0.5 truncate text-[11px] text-fg">
          {eventLabel(moment.eventType)}
        </p>
        <p className="text-[10px] text-fg-dim">{formatTime(moment.timestamp)}</p>
      </div>
    </button>
  );
}
