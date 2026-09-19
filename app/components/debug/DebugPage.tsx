"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { formatFull, formatRelative, TIME_ZONE_LABEL } from "@/lib/format";
import type { Moment } from "@/types/moment";

const POLL_MS = 2000;

interface BackendStatus {
  reachable: boolean;
  reason?: string;
  latencyMs?: number;
  checkedAt?: string;
  eeg?: {
    phase: string;
    signal_connected: boolean;
    clean_calibration_windows: number;
    windows: number;
    channels_used?: string[];
    sampling_rate?: number;
    last_window?: { sample_time_s: number; z_score: number; run: number } | null;
  };
  recording?: {
    state: string;
    phone_connected: boolean;
    media_path: string | null;
    recording_id: string | null;
  };
  library?: { count: number };
  session_dir?: string;
}

function Dot({ ok, warn }: { ok: boolean; warn?: boolean }) {
  return (
    <span
      className={cn(
        "inline-block h-2 w-2 shrink-0 rounded-full",
        ok ? "bg-ok" : warn ? "bg-surprise" : "bg-error",
        ok && "pulse-dot",
      )}
      aria-hidden
    />
  );
}

function Row({
  label,
  value,
  ok,
  warn,
  hint,
}: {
  label: string;
  value: string;
  ok?: boolean;
  warn?: boolean;
  hint?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-6 border-b border-line py-3 last:border-b-0">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-sm text-fg">
          {ok !== undefined ? <Dot ok={ok} warn={warn} /> : null}
          {label}
        </p>
        {hint ? <p className="mt-1 text-[12px] leading-5 text-fg-mute">{hint}</p> : null}
      </div>
      <p className="shrink-0 text-right font-mono text-[12px] text-fg-dim">{value}</p>
    </div>
  );
}

export function DebugPage() {
  const [status, setStatus] = useState<BackendStatus | null>(null);
  const [moments, setMoments] = useState<Moment[]>([]);
  const [tick, setTick] = useState(0);
  const [lastChange, setLastChange] = useState<string | null>(null);
  const previous = useRef<string>("");

  const poll = useCallback(async () => {
    try {
      const [statusResponse, momentsResponse] = await Promise.all([
        fetch("/api/status", { cache: "no-store" }),
        fetch("/api/moments", { cache: "no-store" }),
      ]);
      const nextStatus: BackendStatus = await statusResponse.json();
      const nextMoments = (await momentsResponse.json()).moments ?? [];
      setStatus(nextStatus);
      setMoments(nextMoments);

      // Track when anything meaningful last moved, so a frozen pipeline is obvious
      // rather than looking identical to a working one.
      const fingerprint = JSON.stringify([
        nextStatus.eeg?.windows,
        nextStatus.recording?.state,
        nextStatus.recording?.phone_connected,
        nextMoments.length,
      ]);
      if (fingerprint !== previous.current) {
        previous.current = fingerprint;
        setLastChange(new Date().toISOString());
      }
    } catch {
      setStatus({ reachable: false, reason: "web app could not reach its own API" });
    }
    setTick((value) => value + 1);
  }, []);

  useEffect(() => {
    // Deferred rather than called inline: poll() sets state, and doing that
    // synchronously inside the effect body is what react-hooks/set-state-in-effect warns about.
    const first = window.setTimeout(poll, 0);
    const timer = window.setInterval(poll, POLL_MS);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [poll]);

  const eeg = status?.eeg;
  const rec = status?.recording;
  const captures = moments.filter((moment) => moment.id.startsWith("capture-"));

  return (
    <main className="mx-auto min-h-dvh w-full max-w-3xl px-5 pb-24 pt-24 md:px-8">
      <header className="mb-8">
        <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-fg-dim">
          Diagnostics
        </p>
        <h1 className="mt-3 font-serif text-3xl text-fg md:text-4xl">
          Is anything actually connected?
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-fg-dim">
          Live view of the chain behind this interface: the web app talks to the Python
          backend on the laptop, the backend hands commands to the Android app, and the
          phone uploads what it recorded. Each link is shown separately so a break is
          attributable rather than mysterious. Refreshing every {POLL_MS / 1000}s. All
          times {TIME_ZONE_LABEL}.
        </p>
      </header>

      <section className="mb-10 border border-line bg-bg-panel px-5 py-2">
        <h2 className="border-b border-line py-3 text-[11px] tracking-[0.2em] uppercase text-fg-dim">
          The chain
        </h2>
        <Row
          label="Web app → backend"
          ok={!!status?.reachable}
          value={
            status?.reachable
              ? `${status.latencyMs ?? 0} ms`
              : (status?.reason ?? "checking…")
          }
          hint={
            status?.reachable
              ? "This page reached the backend through the server-side proxy."
              : "Start it: run.py serve --source synthetic --recorder phone --host 0.0.0.0"
          }
        />
        <Row
          label="Backend ← phone"
          ok={!!rec?.phone_connected}
          value={rec?.phone_connected ? "polling" : "silent"}
          hint={
            rec?.phone_connected
              ? "The Android app has asked for commands within the last 5 seconds."
              : "Open the app, tap Register, then Start session. Nothing polls from the Home screen."
          }
        />
        <Row
          label="EEG signal"
          ok={!!eeg?.signal_connected}
          value={eeg?.phase ?? "—"}
          hint={
            eeg?.signal_connected
              ? `${eeg?.windows ?? 0} windows processed · ${eeg?.clean_calibration_windows ?? 0} clean calibration windows · ${eeg?.channels_used?.join(", ") ?? "—"} @ ${eeg?.sampling_rate ?? "—"} Hz`
              : "No EEG arriving. Feed it: feed_synthetic.py calibrate"
          }
        />
        <Row
          label="Recorder"
          ok={rec?.state === "recording"}
          warn={rec?.state === "stopped" || rec?.state === "idle"}
          value={rec?.state ?? "—"}
          hint={
            rec?.state === "error"
              ? "The phone refused or failed a command. Check that preview is live, then send stop to clear."
              : "idle and stopped are both fine between clips; recording means a clip is open."
          }
        />
        <Row
          label="Captured media"
          ok={captures.length > 0}
          value={`${captures.length}`}
          hint="Clips uploaded from the phone and turned into moments."
        />
      </section>

      {eeg?.last_window ? (
        <section className="mb-10 border border-line bg-bg-panel px-5 py-2">
          <h2 className="border-b border-line py-3 text-[11px] tracking-[0.2em] uppercase text-fg-dim">
            Most recent detector window
          </h2>
          <Row
            label="z-score against baseline"
            value={eeg.last_window.z_score >= 0
              ? `+${eeg.last_window.z_score.toFixed(2)}`
              : eeg.last_window.z_score.toFixed(2)}
            hint="How far this window sits from the wearer's own calibrated baseline. Not a probability."
          />
          <Row
            label="Consecutive elevated windows"
            value={`${eeg.last_window.run} of 4`}
            hint="Four in a row are required before a stop fires. This is the persistence filter."
          />
          <Row
            label="Position in session"
            value={`${eeg.last_window.sample_time_s.toFixed(0)}s`}
            hint="Measured in EEG signal time, not wall clock."
          />
        </section>
      ) : null}

      <section className="mb-10 border border-line bg-bg-panel px-5 py-2">
        <h2 className="border-b border-line py-3 text-[11px] tracking-[0.2em] uppercase text-fg-dim">
          Is it moving?
        </h2>
        <Row
          label="Last state change"
          ok={!!lastChange}
          value={lastChange ? formatRelative(lastChange) : "nothing yet"}
          hint="Updates whenever windows, recorder state, phone presence or capture count changes. If this stalls while a session is running, the pipeline is stuck."
        />
        <Row
          label="Poll count this page"
          value={`${tick}`}
          hint="Proves this page is live rather than a stale render."
        />
        <Row
          label="Checked at"
          value={status?.checkedAt ? formatFull(status.checkedAt) : "—"}
        />
        {status?.session_dir ? (
          <Row
            label="Session directory"
            value={status.session_dir.split("/").slice(-1)[0]}
            hint="Where events.jsonl, eeg.jsonl and uploaded media for this run are written."
          />
        ) : null}
      </section>

      <section>
        <h2 className="mb-4 text-[11px] tracking-[0.2em] uppercase text-fg-dim">
          Captured clips ({captures.length})
        </h2>
        {captures.length === 0 ? (
          <p className="border border-line bg-bg-panel p-5 text-sm leading-6 text-fg-dim">
            Nothing uploaded yet. A clip appears here after the detector stops a recording
            and the phone finishes uploading it — usually within a few seconds of the stop.
          </p>
        ) : (
          <ul className="space-y-4">
            {captures.map((moment) => (
              <li key={moment.id} className="border border-line bg-bg-panel">
                <div className="flex gap-4 p-4">
                  {moment.media.thumbnailUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={moment.media.thumbnailUrl}
                      alt=""
                      className="h-24 w-32 shrink-0 border border-line object-cover"
                    />
                  ) : null}
                  <div className="min-w-0">
                    <p className="font-mono text-[11px] tracking-[0.14em] text-accent">
                      {moment.id}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-fg">{moment.summary}</p>
                    <p className="mt-2 font-mono text-[11px] text-fg-dim">
                      {formatFull(moment.timestamp)} · {formatRelative(moment.timestamp)}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-3 font-mono text-[11px]">
                      <Link href={`/moment/${moment.id}`} className="text-accent underline">
                        open moment
                      </Link>
                      {moment.media.videoUrl ? (
                        <a href={moment.media.videoUrl} className="text-accent underline">
                          raw video
                        </a>
                      ) : null}
                    </div>
                  </div>
                </div>
                {moment.media.videoUrl ? (
                  <video
                    src={moment.media.videoUrl}
                    controls
                    playsInline
                    preload="metadata"
                    poster={moment.media.thumbnailUrl || undefined}
                    className="max-h-80 w-full border-t border-line bg-black object-contain"
                  />
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
