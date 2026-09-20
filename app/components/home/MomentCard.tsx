"use client";

import { useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import { IntensityDot } from "@/components/ui/IntensityDot";
import { formatMomentNumber, formatTime } from "@/lib/format";
import { momentTitle } from "@/lib/labels";
import type { Moment } from "@/types/moment";

/** The first processing step still pending, or null once everything is done. */
function pendingStep(moment: Moment): string | null {
  const p = moment.processing;
  if (!p) return null;
  if (p.extraction === "pending") return "Extracting";
  if (p.analysis === "pending") return "Describing";
  if (p.indexing === "pending") return "Indexing";
  return null;
}

export function MomentCard({
  moment,
  selected,
  onSelect,
}: {
  moment: Moment;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const router = useRouter();
  const step = pendingStep(moment);
  return (
    <button
      type="button"
      onClick={() => onSelect(moment.id)}
      // Single click selects (drives the hero); double click opens the moment. Enter
      // opens too, so keyboard users are not left with only the hero's link.
      onDoubleClick={() => router.push(`/moment/${moment.id}`)}
      onKeyDown={(e) => { if (e.key === "Enter") router.push(`/moment/${moment.id}`); }}
      title="Double-click to open"
      aria-pressed={selected}
      className={cn(
        "group relative aspect-video w-[min(80vw,320px)] shrink-0 snap-start overflow-hidden rounded-xl border border-white/10 bg-bg-panel text-left transition-all duration-300 hover:-translate-y-1 md:w-[360px]",
        step && "shimmer border-accent/30",
        selected
          ? "ring-2 ring-accent ring-offset-4 ring-offset-bg brightness-100"
          : "brightness-[0.85] hover:brightness-100",
      )}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {moment.media.thumbnailUrl && <img
        src={moment.media.thumbnailUrl}
        alt=""
        className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
      />}
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />
      <IntensityDot value={moment.confidence} showLabel className="absolute left-4 top-4" />
      {step ? (
        <span
          role="status"
          className="absolute right-4 top-4 flex items-center gap-2 rounded-full border border-accent/40 bg-black/40 px-3 py-1.5 text-[10px] tracking-[0.14em] uppercase text-accent backdrop-blur-md"
        >
          <span className="processing-ring h-3 w-3" aria-hidden />
          {step}…
        </span>
      ) : (
        <span aria-hidden className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-black/25 text-xs backdrop-blur-md">▶</span>
      )}
      <div className="absolute inset-x-0 bottom-0 p-5">
        <p className="text-xs tracking-[0.1em] text-accent">
          {formatMomentNumber(moment.sequence)}{moment.demo ? " · Demo" : ""}
        </p>
        <p className="mt-2 truncate text-lg leading-7 text-fg">
          {momentTitle(moment)}
        </p>
        <p className="mt-1 text-xs text-fg/70">{formatTime(moment.timestamp)}</p>
      </div>
    </button>
  );
}
