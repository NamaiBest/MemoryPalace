"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Demo length. The design target is 30s; 10 keeps a live demo moving. */
export const DEFAULT_CAPTURE_SECONDS = 10;

export type CapturePhase = "idle" | "starting" | "recording" | "stopping" | "saved" | "failed";

async function command(action: "start" | "stop") {
  const response = await fetch("/api/recording", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error ?? `request failed (${response.status})`);
  return payload;
}

/**
 * Wait for the phone to actually confirm a start.
 *
 * /recording/start returns as soon as the command is *queued*; the phone's acceptance or
 * refusal arrives afterwards. Treating the 200 as success meant counting down ten seconds
 * against a recording that had already been rejected, then sending a stop that could only
 * fail with "Recording ID mismatch".
 */
async function waitForRecording(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const status = await (await fetch("/api/status", { cache: "no-store" })).json();
    const state = status?.recording?.state;
    if (state === "recording") return;
    if (state === "error") {
      throw new Error("The phone refused: start the camera preview on it, then try again.");
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("The phone never confirmed the recording started.");
}

/**
 * Record for a fixed number of seconds, then stop.
 *
 * The timer lives in the browser, so a closed tab would leave a recording open. The stop
 * is therefore also sent on unmount, and the backend treats a second stop as a no-op.
 */
export function useTimedCapture(seconds = DEFAULT_CAPTURE_SECONDS) {
  const [phase, setPhase] = useState<CapturePhase>("idle");
  const [remaining, setRemaining] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<number[]>([]);
  const recording = useRef(false);

  const clearTimers = () => {
    timers.current.forEach(window.clearTimeout);
    timers.current.forEach(window.clearInterval);
    timers.current = [];
  };

  useEffect(() => {
    return () => {
      clearTimers();
      // Never leave the phone recording because someone navigated away.
      if (recording.current) void command("stop").catch(() => undefined);
    };
  }, []);

  const capture = useCallback(async () => {
    if (phase !== "idle" && phase !== "saved" && phase !== "failed") return;
    clearTimers();
    setError(null);
    setPhase("starting");

    try {
      await command("start");
      await waitForRecording();
    } catch (failure) {
      setPhase("failed");
      setError(failure instanceof Error ? failure.message : "could not start");
      // A refused start leaves the recorder in "error"; clear it so the next attempt
      // is not blocked by the previous one's wreckage.
      await command("stop").catch(() => undefined);
      return;
    }

    recording.current = true;
    setPhase("recording");
    setRemaining(seconds);

    const tick = window.setInterval(() => {
      setRemaining((value) => (value > 0 ? value - 1 : 0));
    }, 1000);
    timers.current.push(tick);

    const finish = window.setTimeout(async () => {
      window.clearInterval(tick);
      setPhase("stopping");
      try {
        await command("stop");
        recording.current = false;
        setPhase("saved");
        // The clip still has to upload from the phone, so "saved" is not the end of
        // the story — the moment list picks it up a moment later on its own.
        timers.current.push(window.setTimeout(() => setPhase("idle"), 6000));
      } catch (failure) {
        recording.current = false;
        setPhase("failed");
        setError(failure instanceof Error ? failure.message : "could not stop");
      }
    }, seconds * 1000);
    timers.current.push(finish);
  }, [phase, seconds]);

  return { phase, remaining, error, capture, busy: phase !== "idle" && phase !== "saved" && phase !== "failed" };
}
