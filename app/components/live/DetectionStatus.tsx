"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { useTimedCapture, type CapturePhase } from "@/lib/capture";

const COPY: Record<CapturePhase, string> = {
  idle: "Signal processor ready",
  starting: "Opening rear phone camera…",
  recording: "Capturing the moment",
  stopping: "Finalizing video…",
  uploading: "Uploading captured media…",
  extracting: "Extracting the moment…",
  analyzing: "Meta is describing the video…",
  indexing: "Elastic hybrid index update…",
  saved: "Moment added to Memory Palace",
  failed: "Capture needs attention",
};

const STEPS: { label: string; active: CapturePhase[]; done: CapturePhase[] }[] = [
  { label: "Capture", active: ["starting", "recording", "stopping", "uploading"], done: ["extracting", "analyzing", "indexing", "saved"] },
  { label: "Describe", active: ["extracting", "analyzing"], done: ["indexing", "saved"] },
  { label: "Index", active: ["indexing"], done: ["saved"] },
];

export function DetectionStatus({ phoneReady, onTrigger }: {
  phoneReady: boolean;
  onTrigger?: () => void;
}) {
  const [seconds, setSeconds] = useState(10);
  const [threshold, setThreshold] = useState(2);
  const [notice, setNotice] = useState(false);
  const { phase, remaining, error, capture, busy } = useTimedCapture(seconds);

  useEffect(() => {
    const timeout = window.setTimeout(async () => {
      try {
        await fetch("/api/settings/threshold", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: threshold }),
        });
      } catch {
        // Diagnostics exposes the authoritative backend value when it is offline.
      }
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [threshold]);

  const trigger = () => {
    setNotice(true);
    window.setTimeout(() => setNotice(false), 3200);
    onTrigger?.();
    void capture("load");
  };

  return (
    <section className="rounded-[28px] border border-accent/20 bg-bg-panel/75 p-6 shadow-2xl backdrop-blur-xl md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="text-xs tracking-[0.14em] uppercase text-accent">Neural event simulator</p>
          <h2 className="mt-3 font-serif text-3xl">Create a cognitive moment.</h2>
        </div>
        <div role="group" aria-label="Capture duration" className="flex gap-1 rounded-full border border-line-strong p-1">
          {[10, 30].map((length) => (
            <button key={length} type="button" disabled={busy} aria-pressed={seconds === length}
              onClick={() => setSeconds(length)}
              className={cn("rounded-full px-4 py-2 text-sm transition-colors disabled:opacity-50",
                seconds === length ? "bg-accent text-bg" : "text-fg-dim hover:text-fg")}>
              {length}s
            </button>
          ))}
        </div>
      </div>

      <label className="mt-7 block">
        <span className="flex items-center justify-between text-[11px] tracking-[0.14em] uppercase text-fg-dim">
          Detection threshold
          <strong className="font-mono text-accent">z ≥ {threshold.toFixed(1)}</strong>
        </span>
        <input type="range" min="0.5" max="6" step="0.1" value={threshold}
          disabled={busy} onChange={(event) => setThreshold(Number(event.target.value))}
          className="mt-3 w-full accent-[var(--accent)]" />
        <span className="mt-1 block text-xs text-fg-mute">
          Demo control · changes the backend persistence detector threshold.
        </span>
      </label>

      <button type="button" disabled={busy || !phoneReady} onClick={trigger}
        className="mt-7 w-full rounded-2xl bg-accent px-6 py-5 text-base font-semibold text-bg shadow-[0_12px_44px_rgba(201,184,150,.18)] transition hover:bg-fg disabled:cursor-not-allowed disabled:opacity-35">
        Simulate Neural Spike <span aria-hidden className="ml-2">↗</span>
      </button>

      {notice && (
        <div role="alert" className="mt-4 rounded-2xl border border-error/35 bg-error/10 px-4 py-3 text-sm text-fg">
          <span className="mr-2 inline-block h-2 w-2 rounded-full bg-error shadow-[0_0_16px_var(--error)]" />
          Neural spike detected
        </div>
      )}

      <div className="mt-6 rounded-2xl border border-white/10 bg-black/15 p-4">
        <div role="status" aria-live="polite" className="flex items-center gap-3 text-sm">
          <span className={cn("h-2 w-2 shrink-0 rounded-full", busy ? "pulse-dot bg-accent" : phase === "saved" ? "bg-ok" : phase === "failed" ? "bg-error" : "bg-fg-mute")} />
          <p>{COPY[phase]}{phase === "recording" ? ` · ${remaining}s left` : ""}</p>
        </div>
        <ol className="mt-4 grid grid-cols-3 gap-2">
          {STEPS.map((step) => {
            const active = step.active.includes(phase);
            const complete = step.done.includes(phase);
            return (
              <li key={step.label} className={cn("rounded-xl border px-3 py-2 text-center text-[10px] tracking-[0.12em] uppercase",
                complete ? "border-ok/30 bg-ok/10 text-ok" : active ? "border-accent/40 bg-accent/10 text-accent" : "border-white/10 text-fg-mute")}>
                {complete ? "✓ " : ""}{step.label}
              </li>
            );
          })}
        </ol>
      </div>

      {phase === "saved" && <Link href="/" className="mt-4 inline-block text-sm text-accent underline underline-offset-4">Watch your moment →</Link>}
      {error && <p className="mt-4 text-sm leading-6 text-error">{error}</p>}
      <p className="mt-5 text-xs leading-6 text-fg-dim">
        {phoneReady
          ? "Simulated EEG trigger · real rear-phone-camera capture · demo glasses bridge."
          : "Connect the phone app first. Its camera remains off until this button is pressed."}
      </p>
    </section>
  );
}
