"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import { DEFAULT_CAPTURE_SECONDS, useTimedCapture } from "@/lib/capture";

const COPY = {
  idle: "Waiting for a candidate transition",
  starting: "Asking the phone to record…",
  recording: "Recording",
  stopping: "Stopping and saving…",
  saved: "Saved — uploading from the phone",
  failed: "Could not capture",
} as const;

export function DetectionStatus({ phoneReady }: { phoneReady: boolean }) {
  const { phase, remaining, error, capture, busy } = useTimedCapture(DEFAULT_CAPTURE_SECONDS);

  return (
    <section className="border border-line bg-bg-panel p-5">
      <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">Event detection</h2>

      <div className="mt-5 flex items-center gap-3">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            phase === "idle" && "bg-fg-mute",
            phase === "starting" && "bg-accent pulse-dot",
            phase === "recording" && "bg-error pulse-dot",
            phase === "stopping" && "bg-accent pulse-dot",
            phase === "saved" && "bg-ok",
            phase === "failed" && "bg-error",
          )}
        />
        <p className="font-mono text-[13px] uppercase tracking-[0.14em]">
          {COPY[phase]}
          {phase === "recording" ? ` · ${remaining}s left` : ""}
        </p>
      </div>

      {phase === "recording" ? (
        <div className="mt-4 h-[3px] w-full bg-line-strong">
          <div
            className="h-full bg-error transition-[width] duration-1000 ease-linear"
            style={{ width: `${(remaining / DEFAULT_CAPTURE_SECONDS) * 100}%` }}
          />
        </div>
      ) : null}

      {phase === "saved" ? (
        <p className="mt-3 text-sm leading-6 text-fg-dim">
          The phone is uploading the clip. It appears on{" "}
          <Link href="/" className="text-accent underline">
            the home page
          </Link>{" "}
          within a few seconds, no refresh needed.
        </p>
      ) : null}

      {error ? (
        <p className="mt-3 border-l-2 border-error pl-3 text-sm leading-6 text-fg">{error}</p>
      ) : null}

      <div className="mt-7">
        <button
          type="button"
          disabled={busy || !phoneReady}
          onClick={() => void capture()}
          className={cn(
            "w-full border px-4 py-3 text-[11px] tracking-[0.2em] uppercase transition-colors",
            busy || !phoneReady
              ? "cursor-not-allowed border-line text-fg-mute"
              : "border-accent/60 text-accent hover:bg-accent hover:text-bg",
          )}
        >
          {busy ? COPY[phase] : `Capture the next ${DEFAULT_CAPTURE_SECONDS} seconds`}
        </button>

        {!phoneReady ? (
          <p className="mt-3 text-[12px] leading-5 text-fg-mute">
            The phone is not polling, so there is nothing to record with. Open the Android
            app, tap Register, then Start session and Preview.
          </p>
        ) : (
          <p className="mt-3 text-[12px] leading-5 text-fg-mute">
            This records real footage for {DEFAULT_CAPTURE_SECONDS} seconds and saves it as
            a moment. There is one button rather than one per event type because the
            detector measures sustained load and cannot tell surprise from insight from
            error — offering that choice would imply a distinction it cannot make.
          </p>
        )}
      </div>
    </section>
  );
}
