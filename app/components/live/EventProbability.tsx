"use client";

import { eventLabel } from "@/lib/labels";
import { cn } from "@/lib/cn";
import type { EventType } from "@/types/moment";
import type { EventProbabilities } from "@/lib/integrations";

const ORDER = ["surprise", "insight", "error"] as const satisfies readonly EventType[];

const BAR: Record<EventType, string> = {
  surprise: "bg-surprise",
  insight: "bg-insight",
  error: "bg-error",
  load: "bg-load",
};

export function EventProbability({
  probabilities,
}: {
  probabilities: EventProbabilities;
}) {
  return (
    <section className="border border-line bg-bg-panel p-5">
      <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">
        Candidate cognitive transition
      </h2>
      <p className="mt-2 text-sm text-fg-mute">
        Live event probabilities from the detector. These are estimates, not
        identifications of a thought.
      </p>
      <ul className="mt-6 space-y-5">
        {ORDER.map((type) => {
          const value = Math.round(probabilities[type] * 100);
          return (
            <li key={type}>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span>{eventLabel(type)}</span>
                <span className="font-mono text-fg-dim">{value}%</span>
              </div>
              <div className="h-[3px] bg-line-strong">
                <div
                  className={cn("h-full transition-all duration-700", BAR[type])}
                  style={{ width: `${value}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
