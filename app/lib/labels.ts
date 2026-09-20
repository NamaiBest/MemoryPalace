import type { EventType, Modality, Moment, MomentStatus } from "@/types/moment";

export const EVENT_LABELS: Record<EventType, string> = {
  capture: "Live Capture",
  surprise: "Possible Surprise",
  excitement: "Excitement Trigger",
  insight: "Possible Insight",
  error: "Error-related Event",
  load: "Sustained Load",
};

export const EVENT_SHORT_LABELS: Record<EventType, string> = {
  capture: "Captured",
  surprise: "Surprise",
  excitement: "Excitement",
  insight: "Insight",
  error: "Error",
  load: "Load",
};

export const STATUS_LABELS: Record<MomentStatus, string> = {
  candidate: "Candidate",
  kept: "Kept",
  deleted: "Removed",
};

export const MODALITY_LABELS: Record<Modality, string> = {
  eeg: "EEG",
  video: "Video",
};

export function eventLabel(type: EventType): string {
  return EVENT_LABELS[type];
}

export function momentTitle(moment: Moment): string {
  const semantic = moment.semanticTitle?.trim();
  if (semantic) return semantic;
  if (moment.demo) {
    if (moment.eventType === "excitement") return "Exciting moment";
    return moment.eventType === "surprise" ? "Unexpected moment" : "Neural spike moment";
  }
  return EVENT_SHORT_LABELS[moment.eventType] + " moment";
}

export function getModalities(moment: Moment): Modality[] {
  const modalities: Modality[] = [];
  if (moment.eeg) modalities.push("eeg");
  if (moment.media.thumbnailUrl || moment.media.videoUrl) {
    modalities.push("video");
  }
  return modalities;
}

export function formatModalities(moment: Moment): string {
  return getModalities(moment)
    .map((modality) => MODALITY_LABELS[modality])
    .join(" + ");
}
