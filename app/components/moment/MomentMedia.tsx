"use client";

import { useState } from "react";
import { EventLabel } from "@/components/ui/EventLabel";
import { IntensityDot } from "@/components/ui/IntensityDot";
import { formatConfidence, formatTimeWithSeconds } from "@/lib/format";
import type { Moment } from "@/types/moment";

export function MomentMedia({ moment }: { moment: Moment }) {
  const [imageFailed, setImageFailed] = useState(false);
  const [videoFailed, setVideoFailed] = useState(!moment.media.videoUrl);

  return (
    <section className="relative aspect-[16/9] w-full overflow-hidden bg-black lg:aspect-[21/9]">
      <IntensityDot value={moment.confidence} showLabel className="absolute left-5 top-5 z-20 md:left-8 md:top-8" />
      {!imageFailed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={moment.media.thumbnailUrl}
          alt={moment.media.alt}
          className="absolute inset-0 h-full w-full object-cover"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-[#1b1915] to-black" />
      )}
      {moment.media.videoUrl && !videoFailed ? (
        <video
          controls
          playsInline
          preload="metadata"
          poster={moment.media.thumbnailUrl}
          className="absolute inset-0 h-full w-full object-cover"
          onError={() => setVideoFailed(true)}
        >
          <source src={moment.media.videoUrl} type="video/mp4" />
        </video>
      ) : null}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-5 md:p-8">
        <EventLabel
          type={moment.eventType}
          className="text-[11px] tracking-[0.2em] uppercase"
        />
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[12px] text-fg-dim">
          <span>{formatTimeWithSeconds(moment.timestamp)}</span>
          <span>{formatConfidence(moment.confidence)} Spike Intensity</span>
        </div>
      </div>
    </section>
  );
}
