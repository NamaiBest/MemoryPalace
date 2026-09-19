"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { formatRelative } from "@/lib/format";

const POLL_MS = 2000;

interface Status {
  reachable: boolean;
  reason?: string;
  recording?: { state: string; phone_connected: boolean };
  eeg?: { phase: string; signal_connected: boolean };
  library?: { count: number };
}

export function RecordingControl() {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [lastCapture, setLastCapture] = useState<string | null>(null);
  const [captureCount, setCaptureCount] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next: Status = await (await fetch("/api/status", { cache: "no-store" })).json();
      setStatus(next);
      const count = next.library?.count ?? 0;
      setCaptureCount((previous) => {
        // A clip landing while you watch is the payoff, so call it out explicitly
        // rather than letting the number quietly tick up.
        if (previous !== null && count > previous) setLastCapture(new Date().toISOString());
        return count;
      });
    } catch {
      setStatus({ reachable: false, reason: "web app could not reach its own API" });
    }
  }, []);

  useEffect(() => {
    const first = window.setTimeout(refresh, 0);
    const timer = window.setInterval(refresh, POLL_MS);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [refresh]);

  const send = async (action: "start" | "stop") => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch("/api/recording", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const payload = await response.json();
      setMessage(
        response.ok
          ? { text: action === "start" ? "Recording started on the phone." : "Stop sent.", ok: true }
          : { text: payload.error ?? "Request failed.", ok: false },
      );
    } catch (error) {
      setMessage({
        text: error instanceof Error ? error.message : "Request failed.",
        ok: false,
      });
    } finally {
      setBusy(false);
      void refresh();
    }
  };

  const rec = status?.recording;
  const phoneReady = !!rec?.phone_connected;
  const recording = rec?.state === "recording" || rec?.state === "starting";
  const canStart = !!status?.reachable && phoneReady && !recording && !busy;
  const canStop = !!status?.reachable && recording && !busy;

  return (
    <section className="border border-line bg-bg-panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">
            Recording control
          </h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-fg-mute">
            This is the real chain, not the simulation below. Starting here sends a command
            to the phone and records actual footage.
          </p>
        </div>
        <div className="text-right font-mono text-[11px] leading-5">
          <p className={cn(status?.reachable ? "text-ok" : "text-error")}>
            backend {status?.reachable ? "up" : "down"}
          </p>
          <p className={cn(phoneReady ? "text-ok" : "text-fg-mute")}>
            phone {phoneReady ? "connected" : "silent"}
          </p>
          <p className="text-fg-dim">
            {rec?.state ?? "—"}
            {captureCount !== null ? ` · ${captureCount} clips` : ""}
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={!canStart}
          onClick={() => send("start")}
          className={cn(
            "border px-5 py-2.5 text-[11px] tracking-[0.2em] uppercase transition-colors",
            canStart
              ? "border-accent/60 text-accent hover:bg-accent hover:text-bg"
              : "cursor-not-allowed border-line text-fg-mute",
          )}
        >
          {busy ? "working…" : "Start recording"}
        </button>
        <button
          type="button"
          disabled={!canStop}
          onClick={() => send("stop")}
          className={cn(
            "border px-5 py-2.5 text-[11px] tracking-[0.2em] uppercase transition-colors",
            canStop
              ? "border-error/60 text-error hover:bg-error hover:text-bg"
              : "cursor-not-allowed border-line text-fg-mute",
          )}
        >
          Stop and save
        </button>
        <Link
          href="/debug"
          className="text-[11px] tracking-[0.2em] uppercase text-fg-dim underline hover:text-fg"
        >
          Diagnostics
        </Link>
      </div>

      {message ? (
        <p
          className={cn(
            "mt-4 border-l-2 pl-3 text-sm leading-6",
            message.ok ? "border-ok text-fg-dim" : "border-error text-fg",
          )}
        >
          {message.text}
        </p>
      ) : null}

      {!phoneReady && status?.reachable ? (
        <p className="mt-4 text-[12px] leading-5 text-fg-mute">
          The phone is not polling. Open the Android app, tap Register, then Start session
          and Preview — nothing polls from the Home screen, and a recording cannot start
          until the camera stream is actually live.
        </p>
      ) : null}

      {!status?.reachable ? (
        <p className="mt-4 text-[12px] leading-5 text-fg-mute">
          Backend unreachable{status?.reason ? `: ${status.reason}` : ""}. Start it with
          run.py serve --source synthetic --recorder phone --host 0.0.0.0
        </p>
      ) : null}

      {lastCapture ? (
        <p className="mt-4 text-[12px] leading-5 text-ok">
          A clip finished uploading {formatRelative(lastCapture)} — it is on the home page now.
        </p>
      ) : null}
    </section>
  );
}
