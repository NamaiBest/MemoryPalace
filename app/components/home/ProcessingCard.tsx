"use client";

import type { CaptureActivity } from "@/lib/useCaptureActivity";

const COPY: Record<CaptureActivity["phase"], { title: string; detail: string }> = {
  recording: { title: "Recording", detail: "The phone camera is open." },
  stopping: { title: "Saving", detail: "Finalising the clip on the phone." },
  uploading: { title: "Uploading", detail: "Sending the clip to the laptop." },
};

/**
 * Stands in for a moment that does not exist yet. Occupies the same slot and size as a
 * real card, so the gallery visibly grows the instant a capture starts rather than
 * staying still for the ~30 s it takes to record, save and upload.
 */
export function ProcessingCard({ activity }: { activity: CaptureActivity }) {
  const copy = COPY[activity.phase];
  return (
    <div
      role="status"
      aria-live="polite"
      className="shimmer relative aspect-video w-[min(80vw,320px)] shrink-0 snap-start overflow-hidden rounded-xl border border-accent/30 bg-bg-panel md:w-[360px]"
    >
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />
      <div className="absolute left-4 top-4 flex items-center gap-2">
        <span className="processing-ring h-4 w-4" aria-hidden />
        <span className="text-[10px] tracking-[0.16em] uppercase text-accent">
          {activity.phase === "recording" && activity.remaining !== null
            ? `${activity.remaining}s left`
            : "in progress"}
        </span>
      </div>
      <div className="absolute inset-x-0 bottom-0 p-5">
        <p className="text-xs tracking-[0.1em] text-accent">New moment</p>
        <p className="mt-2 text-lg leading-7 text-fg">{copy.title}…</p>
        <p className="mt-1 text-xs text-fg/70">{copy.detail}</p>
      </div>
    </div>
  );
}
