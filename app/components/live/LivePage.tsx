"use client";

import { useEffect, useState } from "react";
import { DetectionStatus } from "@/components/live/DetectionStatus";
import { EEGMonitor } from "@/components/live/EEGMonitor";
import { RecordingControl } from "@/components/live/RecordingControl";

export function LivePage() {
  const [phoneReady, setPhoneReady] = useState(false);
  const [glassesConnected, setGlassesConnected] = useState(false);
  const [burstId, setBurstId] = useState(0);
  const [sessionSeconds, setSessionSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setSessionSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

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

  const elapsed = `${String(Math.floor(sessionSeconds / 60)).padStart(2, "0")}:${String(sessionSeconds % 60).padStart(2, "0")}`;

  return (
    <main className="mx-auto max-w-[1500px] px-6 pb-24 pt-32 md:px-12 md:pt-36">
      <header className="flex flex-wrap items-end justify-between gap-8">
        <div>
          <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">MemoryPalace / Live demo</p>
          <h1 className="mt-4 font-serif text-5xl md:text-6xl">Watch a moment form.</h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-fg-dim">
            Eight simulated EEG channels drive a real phone-camera capture, followed by
            durable moment extraction and Elastic indexing.
          </p>
        </div>
        <div className="rounded-2xl border border-line bg-bg-panel/65 px-5 py-3 text-right backdrop-blur-xl">
          <p className="text-[10px] tracking-[0.16em] uppercase text-fg-mute">Session duration</p>
          <p className="mt-1 font-mono text-2xl text-fg">{elapsed}</p>
        </div>
      </header>

      <section className="mt-8 grid gap-3 sm:grid-cols-3">
        <ConnectionCard label="EEG headset" value="Connected" detail="Simulated 8-channel Crown" ready />
        <ConnectionCard label="Phone camera" value={phoneReady ? "Connected" : "Offline"}
          detail={phoneReady ? "Rear camera · camera currently off" : "Open the Android demo app"} ready={phoneReady} />
        <div className="rounded-2xl border border-line bg-bg-panel/55 px-5 py-4 backdrop-blur-xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] tracking-[0.16em] uppercase text-fg-mute">Smart glasses</p>
              <p className={glassesConnected ? "mt-1 text-sm text-ok" : "mt-1 text-sm text-fg"}>
                {glassesConnected ? "Glasses Connected" : "Not connected"}
              </p>
              <p className="mt-1 text-xs text-fg-mute">Simulated integration · demo mode</p>
            </div>
            <button type="button" onClick={() => setGlassesConnected(true)} disabled={glassesConnected}
              className="rounded-full border border-accent/30 px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-accent disabled:border-ok/25 disabled:text-ok">
              {glassesConnected ? "Connected" : "Connect Glasses"}
            </button>
          </div>
        </div>
      </section>

      <div className="mt-6 grid items-stretch gap-6 xl:grid-cols-[1.45fr_.8fr]">
        <EEGMonitor burstId={burstId} />
        <DetectionStatus phoneReady={phoneReady} onTrigger={() => setBurstId(Date.now())} />
      </div>

      <div className="mt-6">
        <RecordingControl />
      </div>
    </main>
  );
}

function ConnectionCard({ label, value, detail, ready }: {
  label: string;
  value: string;
  detail: string;
  ready: boolean;
}) {
  return (
    <div className="rounded-2xl border border-line bg-bg-panel/55 px-5 py-4 backdrop-blur-xl">
      <p className="text-[10px] tracking-[0.16em] uppercase text-fg-mute">{label}</p>
      <p className={`mt-1 flex items-center gap-2 text-sm ${ready ? "text-ok" : "text-fg"}`}>
        <span className={`h-2 w-2 rounded-full ${ready ? "bg-ok" : "bg-fg-mute"}`} />
        {value}
      </p>
      <p className="mt-1 text-xs text-fg-mute">{detail}</p>
    </div>
  );
}
