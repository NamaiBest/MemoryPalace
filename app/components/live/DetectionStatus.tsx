"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { useTimedCapture, type CapturePhase } from "@/lib/capture";
import { momentTitle } from "@/lib/labels";

const COPY: Record<CapturePhase, string> = {
  idle: "Signal processor ready",
  starting: "Opening rear phone camera…",
  recording: "Capturing the moment",
  stopping: "Finalizing video…",
  uploading: "Uploading captured media…",
  extracting: "Extracting the moment…",
  analyzing: "Meta is describing the video…",
  indexing: "Semantically indexing in Elastic…",
  saved: "Moment added to Memory Palace",
  failed: "Capture needs attention",
};

const STEPS: { label: string; active: CapturePhase[]; done: CapturePhase[] }[] = [
  { label: "Capture", active: ["starting", "recording", "stopping", "uploading"], done: ["extracting", "analyzing", "indexing", "saved"] },
  { label: "Describe", active: ["extracting", "analyzing"], done: ["indexing", "saved"] },
  { label: "Index", active: ["indexing"], done: ["saved"] },
];

const BASE_PROGRESS: Record<CapturePhase, number> = {
  idle: 0,
  starting: 6,
  recording: 12,
  stopping: 58,
  uploading: 66,
  extracting: 73,
  analyzing: 82,
  indexing: 93,
  saved: 100,
  failed: 100,
};

function CaptureRing({ phase, remaining, seconds }: {
  phase: CapturePhase;
  remaining: number;
  seconds: number;
}) {
  const progress = phase === "recording"
    ? 12 + ((seconds - Math.min(seconds, remaining)) / seconds) * 44
    : BASE_PROGRESS[phase];
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - progress / 100);
  const center = phase === "recording"
    ? `${remaining}s`
    : phase === "saved"
      ? "✓"
      : phase === "analyzing"
        ? "AI"
        : phase === "indexing"
          ? "IDX"
          : `${Math.round(progress)}%`;

  return (
    <div className="relative h-28 w-28 shrink-0" aria-label={`${Math.round(progress)} percent complete`}>
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="6" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={phase === "failed" ? "var(--error)" : phase === "saved" ? "var(--ok)" : "var(--accent)"}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <span className={cn(
          "font-mono text-lg",
          phase === "saved" ? "text-ok" : phase === "failed" ? "text-error" : "text-fg",
        )}>{center}</span>
      </div>
    </div>
  );
}

export function DetectionStatus({ phoneReady, onTrigger }: {
  phoneReady: boolean;
  onTrigger?: () => void;
}) {
  const [seconds, setSeconds] = useState(10);
  const [threshold, setThreshold] = useState(2);
  const [notice, setNotice] = useState(false);
  const { phase, remaining, error, capturedMoment, capture, busy } = useTimedCapture(seconds);
  const searchTerm = capturedMoment?.keywords?.find((keyword) => keyword.length > 2)
    ?? capturedMoment?.semanticTitle
    ?? "";

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
    void capture("excitement");
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
          Neural spike detected · recording the next {seconds} seconds
        </div>
      )}

      <div className="mt-6 rounded-2xl border border-white/10 bg-black/15 p-4">
        <div className="flex items-center gap-5">
          <CaptureRing phase={phase} remaining={remaining} seconds={seconds} />
          <div role="status" aria-live="polite" className="min-w-0">
            <p className="text-[10px] tracking-[0.14em] text-fg-mute uppercase">
              Live memory pipeline
            </p>
            <p className="mt-2 text-sm leading-6 text-fg">
              {COPY[phase]}{phase === "recording" ? ` · ${remaining}s left` : ""}
            </p>
            <p className="mt-1 text-xs leading-5 text-fg-mute">
              Progress advances only when the phone and backend confirm each stage.
            </p>
          </div>
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

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <PipelineBar
            label="Meta understanding"
            state={phase === "analyzing" ? "active" : ["indexing", "saved"].includes(phase) ? "done" : "waiting"}
          />
          <PipelineBar
            label="Elastic semantic indexing"
            state={phase === "indexing" ? "active" : phase === "saved" ? "done" : "waiting"}
          />
        </div>
      </div>

      {capturedMoment ? (
        <div className={cn(
          "mt-4 overflow-hidden rounded-2xl border",
          phase === "saved" ? "border-ok/25 bg-ok/[.06]" : "border-accent/20 bg-accent/[.04]",
        )}>
          <div className="flex gap-4 p-4">
            {capturedMoment.media.thumbnailUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={capturedMoment.media.thumbnailUrl} alt="" className="h-24 w-32 shrink-0 rounded-xl object-cover" />
            ) : null}
            <div className="min-w-0">
              <p className={cn(
                "text-[10px] tracking-[0.14em] uppercase",
                phase === "saved" ? "text-ok" : "text-accent",
              )}>{phase === "saved" ? "Search-ready memory" : "New memory received"}</p>
              <p className="mt-1 truncate text-sm font-medium text-fg">{momentTitle(capturedMoment)}</p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-fg-dim">
                {capturedMoment.aiDescription || capturedMoment.summary}
              </p>
            </div>
          </div>
          {phase === "saved" ? (
            <div className="flex flex-wrap gap-3 border-t border-white/10 px-4 py-3 text-xs">
              <Link href={`/moment/${capturedMoment.id}`} className="text-accent underline underline-offset-4">
                Watch moment
              </Link>
              {searchTerm ? (
                <Link href={`/explore?q=${encodeURIComponent(searchTerm)}`} className="text-accent underline underline-offset-4">
                  Search “{searchTerm}”
                </Link>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
      {error && <p className="mt-4 text-sm leading-6 text-error">{error}</p>}
      <p className="mt-5 text-xs leading-6 text-fg-dim">
        {phoneReady
          ? "Simulated EEG trigger · real rear-phone-camera capture · demo glasses bridge."
          : "Connect the phone app first. Its camera remains off until this button is pressed."}
      </p>
    </section>
  );
}

function PipelineBar({ label, state }: {
  label: string;
  state: "waiting" | "active" | "done";
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] tracking-[0.1em] uppercase">
        <span className={state === "waiting" ? "text-fg-mute" : state === "done" ? "text-ok" : "text-accent"}>
          {label}
        </span>
        <span className="font-mono text-fg-mute">
          {state === "done" ? "100%" : state === "active" ? "working" : "queued"}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/[.07]">
        <div className={cn(
          "h-full rounded-full transition-all duration-700",
          state === "done" && "w-full bg-ok",
          state === "active" && "w-2/3 animate-pulse bg-accent",
          state === "waiting" && "w-0",
        )} />
      </div>
    </div>
  );
}
