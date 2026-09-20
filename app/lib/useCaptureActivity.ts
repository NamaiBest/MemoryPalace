"use client";

import { useEffect, useState } from "react";

const POLL_MS = 1000;

export type ActivityPhase = "recording" | "stopping" | "uploading";

export interface CaptureActivity {
  phase: ActivityPhase;
  recordingId: string | null;
  /** Seconds left in the recording, when known. */
  remaining: number | null;
}

/**
 * Whether a capture is in flight on the phone right now.
 *
 * A moment only exists once the phone has finished uploading, so between pressing
 * "capture" and the clip appearing there is nothing in the moment list at all — up to
 * half a minute of apparent silence. This watches /api/status for that window so the
 * gallery can show something is happening rather than nothing.
 *
 * "uploading" is inferred: the recorder reports "stopped" with a recording id that has
 * not yet appeared in the library. The phone does not report upload progress.
 */
export function useCaptureActivity(knownRecordingIds: Set<string>): CaptureActivity | null {
  const [activity, setActivity] = useState<CaptureActivity | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const status = await (await fetch("/api/status", { cache: "no-store" })).json();
        if (cancelled) return;
        const rec = status?.recording;
        const timed = status?.timed_capture;
        const recordingId: string | null = rec?.recording_id ?? null;

        if (rec?.state === "recording" || rec?.state === "starting") {
          const remaining = timed?.ends_at ? Math.max(0, Math.ceil(timed.ends_at - Date.now() / 1000)) : null;
          setActivity({ phase: "recording", recordingId, remaining });
        } else if (rec?.state === "stopping") {
          setActivity({ phase: "stopping", recordingId, remaining: null });
        } else if (rec?.state === "stopped" && recordingId && !knownRecordingIds.has(recordingId)) {
          setActivity({ phase: "uploading", recordingId, remaining: null });
        } else {
          setActivity(null);
        }
      } catch {
        if (!cancelled) setActivity(null);
      }
    };
    const first = window.setTimeout(poll, 0);
    const timer = window.setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [knownRecordingIds]);

  return activity;
}
