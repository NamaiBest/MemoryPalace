"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Moment } from "@/types/moment";

export const DEFAULT_CAPTURE_SECONDS = 10;
export type CapturePhase = "idle" | "starting" | "recording" | "stopping" | "uploading" | "extracting" | "analyzing" | "indexing" | "saved" | "failed";
export type DemoEvent = "excitement" | "load";

/** The backend owns the stop timer, so leaving this page cannot extend a clip. */
export function useTimedCapture(seconds = DEFAULT_CAPTURE_SECONDS) {
  const [phase, setPhase] = useState<CapturePhase>("idle");
  const [remaining, setRemaining] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [capturedMoment, setCapturedMoment] = useState<Moment | null>(null);
  const inFlight = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const capture = useCallback(async (event: DemoEvent = "load") => {
    if (inFlight.current) return;
    inFlight.current = true;
    setError(null);
    setCapturedMoment(null);
    setRemaining(seconds);
    setPhase("starting");
    try {
      const response = await fetch("/api/recording", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "capture", seconds, demo_event: event }),
        signal: AbortSignal.timeout(10000),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error ?? "Could not start capture.");
      const id = payload.recording?.recording_id;
      if (!id) throw new Error("The server did not return a recording ID.");
      const deadline = Date.now() + (seconds + 150) * 1000;
      while (mounted.current && Date.now() < deadline) {
        const statusResponse = await fetch("/api/status", {
          cache: "no-store", signal: AbortSignal.timeout(15000),
        });
        const status = await statusResponse.json();
        if (!status.reachable) throw new Error("Server disconnected. Check the phone and Diagnostics.");
        const rec = status.recording;
        if (rec?.recording_id === id) {
          if (rec.state === "error") throw new Error("The phone could not complete the capture. Check its permissions and connection.");
          if (rec.state === "recording") {
            setPhase("recording");
            const end = status.timed_capture?.ends_at;
            setRemaining(end ? Math.max(0, Math.ceil(end - Date.now() / 1000)) : seconds);
          } else if (rec.state === "stopping") setPhase("stopping");
          else if (rec.state === "stopped") setPhase("uploading");
        }
        // Success means this exact clip reached the library, not just that stop was queued.
        if (rec?.state === "stopped" || rec?.recording_id !== id) {
          const library = await (await fetch("/api/moments", {
            cache: "no-store", signal: AbortSignal.timeout(15000),
          })).json();
          const moment = library.moments?.find((item: { recordingId?: string }) =>
            item.recordingId === id,
          ) as Moment | undefined;
          if (moment) {
            if (mounted.current) setCapturedMoment(moment);
            const processing = moment.processing;
            if (!processing) {
              if (mounted.current) {
                setPhase("saved");
              }
              return;
            }
            if (processing.extraction === "failed") {
              throw new Error("The video was uploaded, but moment extraction failed.");
            }
            if (processing.analysis === "failed") {
              throw new Error("The video is safe, but Meta could not describe it yet.");
            }
            if (processing.indexing === "failed") {
              throw new Error("The video is safe, but Elastic indexing needs a retry.");
            }
            if (processing.extraction !== "complete") setPhase("extracting");
            else if (processing.analysis === "pending") setPhase("analyzing");
            else if (processing.indexing === "pending") setPhase("indexing");
            else {
              if (mounted.current) {
                setPhase("saved");
              }
              return;
            }
          }
        }
        await new Promise((resolve) => setTimeout(resolve, 750));
      }
      if (mounted.current) throw new Error("The moment has not finished uploading. Check Diagnostics.");
    } catch (failure) {
      if (mounted.current) {
        setPhase("failed");
        setError(failure instanceof Error ? failure.message : "Could not capture the moment.");
      }
    } finally {
      inFlight.current = false;
    }
  }, [seconds]);

  return { phase, remaining, error, capturedMoment, capture,
    busy: !["idle", "saved", "failed"].includes(phase) };
}
