/**
 * Future integration boundaries.
 *
 * The UI never talks to OpenBCI, BrainFlow, MediaMTX, RTMP, RTSP,
 * OpenCV, or Ray-Ban Meta hardware directly. Those systems should
 * publish Moments (and optional live streams) through the backend.
 *
 * Swap points:
 * - loadMoments / persistMoment  → REST or database
 * - subscribeEEG                 → backend WebSocket of detector output
 * - resolveCameraSource          → backend-provided POV stream URL
 */

import type { EventType, Moment } from "@/types/moment";

export interface LiveEEGFrame {
  timestamp: number;
  sampleRateHz: number;
  channels: number[];
}

export interface CameraSource {
  kind: "simulated" | "stream";
  url?: string;
  label: string;
}

export interface EventProbabilities {
  surprise: number;
  insight: number;
  error: number;
}

/**
 * Moments captured by the hardware backend, or null when it is unreachable — which is
 * the normal case with no session running. Callers keep their seed data on null.
 */
export async function loadMoments(): Promise<Moment[] | null> {
  try {
    const response = await fetch("/api/moments", { cache: "no-store" });
    if (!response.ok) return null;
    const body = (await response.json()) as { moments?: Moment[] };
    return body.moments?.length ? body.moments : null;
  } catch {
    return null;
  }
}

export async function persistMoment(moment: Moment): Promise<void> {
  // Later: POST /api/moments
  void moment;
}

export function subscribeEEG(
  onFrame: (frame: LiveEEGFrame) => void,
): (() => void) | null {
  // Later: websocket from the EEG event API
  void onFrame;
  return null;
}

export function resolveCameraSource(): CameraSource {
  // Later: return { kind: "stream", url: backendStreamUrl, label: "POV" }
  return {
    kind: "simulated",
    label: "POV context · simulated feed",
  };
}

export function subscribeEventProbabilities(
  onUpdate: (probabilities: EventProbabilities) => void,
): (() => void) | null {
  // Later: websocket from the cognitive-transition detector
  void onUpdate;
  return null;
}

export function reportSimulatedEvent(type: EventType): void {
  // Development-only. Hardware detections will arrive from the backend.
  void type;
}
