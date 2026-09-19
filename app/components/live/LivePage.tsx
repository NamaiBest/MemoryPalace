"use client";

import { useEffect, useState } from "react";
import { CameraFeed } from "@/components/live/CameraFeed";
import { DetectionStatus } from "@/components/live/DetectionStatus";
import { EEGMonitor } from "@/components/live/EEGMonitor";
import { EventProbability } from "@/components/live/EventProbability";
import { RecordingControl } from "@/components/live/RecordingControl";
import type { EventProbabilities } from "@/lib/integrations";

const BASE: EventProbabilities = {
  surprise: 0.22,
  insight: 0.18,
  error: 0.14,
};

export function LivePage() {
  const [probabilities, setProbabilities] = useState<EventProbabilities>(BASE);
  const [phoneReady, setPhoneReady] = useState(false);

  useEffect(() => {
    const poll = async () => {
      try {
        const status = await (await fetch("/api/status", { cache: "no-store" })).json();
        setPhoneReady(!!status?.recording?.phone_connected);
      } catch {
        setPhoneReady(false);
      }
    };
    const first = window.setTimeout(poll, 0);
    const timer = window.setInterval(poll, 2000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, []);

  // Drifting numbers for the simulated panels below the rule. Nothing here is measured.
  useEffect(() => {
    const timer = window.setInterval(() => {
      setProbabilities((current) => ({
        surprise: clamp(current.surprise + jitter()),
        insight: clamp(current.insight + jitter()),
        error: clamp(current.error + jitter()),
      }));
    }, 1400);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <main className="mx-auto max-w-[1500px] px-5 pb-20 pt-24 md:px-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">
            MemoryPalace / Live
          </p>
          <h1 className="mt-3 font-serif text-4xl">Monitoring</h1>
          <p className="mt-3 max-w-lg text-sm leading-6 text-fg-dim">
            The two panels below drive the real phone. Everything under the rule is a
            simulation of what a session looks like — those traces and probabilities are
            generated in the browser, not measured.
          </p>
        </div>
        <p
          className={
            phoneReady
              ? "inline-flex items-center gap-2 font-mono text-[11px] tracking-[0.2em] uppercase text-ok"
              : "inline-flex items-center gap-2 font-mono text-[11px] tracking-[0.2em] uppercase text-fg-mute"
          }
        >
          <span
            className={
              phoneReady
                ? "pulse-dot h-2 w-2 rounded-full bg-ok"
                : "h-2 w-2 rounded-full bg-fg-mute"
            }
          />
          {phoneReady ? "Phone connected" : "Phone silent"}
        </p>
      </header>

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <RecordingControl />
        <DetectionStatus phoneReady={phoneReady} />
      </div>

      <p className="mt-12 border-t border-line pt-6 text-[11px] tracking-[0.2em] uppercase text-fg-mute">
        Simulated below this line
      </p>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.35fr_1fr]">
        <EEGMonitor burst={0} />
        <CameraFeed capturing={false} />
      </div>

      <div className="mt-4">
        <EventProbability probabilities={probabilities} />
      </div>
    </main>
  );
}

function clamp(value: number): number {
  return Math.min(0.94, Math.max(0.08, value));
}

function jitter(): number {
  return (Math.random() - 0.5) * 0.08;
}
