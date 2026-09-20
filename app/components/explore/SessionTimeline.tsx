import Link from "next/link";
import { formatTime } from "@/lib/format";
import { INTENSITY, intensityMeta } from "@/lib/intensity";
import type { Moment } from "@/types/moment";

const AXIS_START = 2;
const AXIS_END = 98;
/** Widest a dot gets, as a share of the track, plus a little breathing room. */
const MIN_GAP = 2.6;

/**
 * Nudge overlapping markers apart while keeping them in chronological order.
 *
 * Captures cluster: a session produces six moments inside a couple of minutes and then
 * nothing for hours, so honest time positioning stacks those six on top of each other
 * and the cluster reads as one dot. This walks left to right enforcing a minimum gap,
 * then walks back from the right edge if the run overflowed the axis. Order is always
 * preserved and each marker still carries its exact timestamp in the tooltip; only the
 * pixel position is approximate, and only where markers would otherwise collide.
 */
function spreadPositions(sorted: number[]) {
  const gap = Math.min(MIN_GAP, (AXIS_END - AXIS_START) / Math.max(1, sorted.length - 1));
  const out = [...sorted];
  for (let i = 1; i < out.length; i += 1) {
    out[i] = Math.max(out[i], out[i - 1] + gap);
  }
  if (out[out.length - 1] > AXIS_END) {
    out[out.length - 1] = AXIS_END;
    for (let i = out.length - 2; i >= 0; i -= 1) {
      out[i] = Math.min(out[i], out[i + 1] - gap);
    }
  }
  return out.map((value) => Math.min(AXIS_END, Math.max(AXIS_START, value)));
}

function durationLabel(milliseconds: number) {
  const seconds = Math.max(0, Math.round(milliseconds / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder ? `${minutes}m ${remainder}s` : `${minutes}m`;
}

export function SessionTimeline({
  moments,
  sessionMoments = moments,
}: {
  moments: Moment[];
  sessionMoments?: Moment[];
}) {
  if (!sessionMoments.length) return null;

  const chronological = [...moments].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
  const completeSession = [...sessionMoments].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
  const start = Math.min(
    ...completeSession.map((moment) => new Date(moment.contextWindow.start).getTime()),
  );
  const end = Math.max(
    ...completeSession.map((moment) => new Date(moment.contextWindow.end).getTime()),
  );
  const span = Math.max(1, end - start);
  const positions = spreadPositions(
    chronological.map((moment) =>
      chronological.length === 1
        ? 50
        : AXIS_START
          + ((new Date(moment.timestamp).getTime() - start) / span) * (AXIS_END - AXIS_START),
    ),
  );

  return (
    <section className="mt-10 rounded-2xl border border-line bg-bg-raised/70 px-5 py-5 md:px-7">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] tracking-[0.18em] uppercase text-accent">
            Session timeline
          </p>
          <p className="mt-1 text-sm text-fg-dim">
            {durationLabel(span)} · {chronological.length} shown of {completeSession.length} captured
          </p>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[9px] tracking-[0.1em] uppercase text-fg-mute">
          {(["weak", "moderate", "high", "critical"] as const).map((level) => (
            <span key={level} className="inline-flex items-center gap-1.5">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: INTENSITY[level].color }}
              />
              {level}
            </span>
          ))}
        </div>
      </div>

      <div className="relative mt-7 h-16" aria-label="Clickable moments across the session">
        <div className="absolute inset-x-0 top-7 h-px bg-gradient-to-r from-line via-line-strong to-line" />
        {chronological.map((moment, index) => {
          const position = positions[index];
          const intensity = intensityMeta(moment.confidence);
          const size = 11 + Math.round(moment.confidence * 8);
          return (
            <Link
              key={moment.id}
              href={`/moment/${moment.id}`}
              className="group absolute top-7 -translate-x-1/2 -translate-y-1/2 rounded-full focus-visible:outline-none"
              style={{ left: `${position}%` }}
              title={`${intensity.label} · ${formatTime(moment.timestamp)} · open moment`}
              aria-label={`Open ${intensity.label.toLowerCase()} intensity moment at ${formatTime(moment.timestamp)}`}
            >
              <span
                className="block rounded-full border-2 border-bg transition-transform group-hover:scale-150 group-focus-visible:scale-150"
                style={{
                  width: size,
                  height: size,
                  backgroundColor: intensity.color,
                  boxShadow: `0 0 16px ${intensity.color}99`,
                }}
              />
            </Link>
          );
        })}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-fg-mute">
        <span>{formatTime(new Date(start).toISOString())}</span>
        <span>{formatTime(new Date(end).toISOString())}</span>
      </div>
    </section>
  );
}
