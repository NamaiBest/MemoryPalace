"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { formatRelative } from "@/lib/format";
import type { Moment } from "@/types/moment";
import { momentTitle } from "@/lib/labels";

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
  const [latestMoment, setLatestMoment] = useState<Moment | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next: Status = await (await fetch("/api/status", { cache: "no-store" })).json();
      setStatus(next);
      const library = await (await fetch("/api/moments", { cache: "no-store" })).json();
      const newest = [...(library.moments ?? [])].sort((a: Moment, b: Moment) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      )[0] as Moment | undefined;
      setLatestMoment(newest ?? null);
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
  const canStop = !!status?.reachable && (recording || rec?.state === "error") && !busy;

  return (
    <section className="rounded-2xl border border-line bg-bg-panel/60 p-6 backdrop-blur-xl md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xs tracking-[0.14em] uppercase text-fg-dim">
            Your session
          </h2>
          <p className="mt-4 max-w-md text-sm leading-7 text-fg-dim">
            Stay connected, capture when it matters. Your phone camera opens only for a
            moment and closes as soon as the recording finishes.
          </p>
        </div>
        <div className="shrink-0 font-mono text-xs leading-7">
          <p className={cn(status?.reachable ? "text-ok" : "text-error")}>
            backend {status?.reachable ? "up" : "down"}
          </p>
          <p className={cn(phoneReady ? "text-ok" : "text-fg-mute")}>
            phone {phoneReady ? "connected" : "offline"}
          </p>
          <p className="text-fg-dim">
            {rec?.state ?? "—"}
            {captureCount !== null ? ` · ${captureCount} clips` : ""}
          </p>
        </div>
      </div>

      <div className="mt-7 flex flex-wrap items-center gap-5">
        <button
          type="button"
          disabled={!canStop}
          onClick={() => send("stop")}
          className={cn(
            "rounded-xl border px-5 py-3 text-sm transition-colors",
            canStop
              ? "border-error/60 text-error hover:bg-error hover:text-bg"
              : "cursor-not-allowed border-line text-fg-mute",
          )}
        >
          {rec?.state === "error" ? "Reset capture" : "Finish early"}
        </button>
        <Link
          href="/debug"
          className="text-sm text-fg-dim underline underline-offset-4 hover:text-fg"
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
          Open the phone app and tap Pair Meta glasses. Demo pairing connects the session
          while leaving the camera off.
        </p>
      ) : null}

      {!status?.reachable ? (
        <p className="mt-4 text-[12px] leading-5 text-fg-mute">
          Waiting for the MemoryPalace server. See Diagnostics for connection details.
        </p>
      ) : null}

      {lastCapture ? (
        <p className="mt-4 text-[12px] leading-5 text-ok">
          A clip finished uploading {formatRelative(lastCapture)} — it is on the home page now.
        </p>
      ) : null}

      {latestMoment ? (
        <Link href={`/moment/${latestMoment.id}`}
          className="mt-6 grid overflow-hidden rounded-2xl border border-white/10 bg-black/15 transition hover:border-accent/30 sm:grid-cols-[180px_1fr]">
          <div className="min-h-28 bg-bg">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {latestMoment.media.thumbnailUrl ? <img src={latestMoment.media.thumbnailUrl} alt=""
              className="h-full w-full object-cover" /> : <div className="grid h-full place-items-center text-fg-mute">▶</div>}
          </div>
          <div className="p-4">
            <p className="text-[10px] tracking-[0.16em] uppercase text-accent">Recently captured</p>
            <p className="mt-2 font-medium text-fg">{momentTitle(latestMoment)}</p>
            <p className="mt-1 text-sm leading-6 text-fg-dim">{latestMoment.aiDescription ?? latestMoment.summary}</p>
            <p className="mt-2 font-mono text-[10px] text-fg-mute">
              {latestMoment.processing?.indexing === "complete" ? "Search index ready" : "Moment saved locally"}
            </p>
          </div>
        </Link>
      ) : null}
    </section>
  );
}
