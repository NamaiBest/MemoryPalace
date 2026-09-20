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

/**
 * Below this ranking score, the event category is not asserted.
 *
 * "surprise", "excitement" and "insight" are inferred categories, and an EEG deviation
 * on its own cannot establish which one occurred. Forcing a weak detection into one of
 * them invents a claim the pipeline cannot support, and it is the first thing a judge
 * would push on. Saying "Uncategorized" costs nothing and is simply true: something
 * stood out, and we are not pretending to know what.
 *
 * "capture" and "load" are exempt. A live capture is a button the wearer pressed, and
 * sustained load is what the detector actually measures rather than an inferred feeling.
 */
export const CATEGORY_CONFIDENCE_THRESHOLD = 0.6;

const INFERRED_EVENTS: ReadonlySet<EventType> = new Set<EventType>([
  "surprise",
  "excitement",
  "insight",
  "error",
]);

export const UNCATEGORIZED_LABEL = "Uncategorized";
export const UNCATEGORIZED_SHORT_LABEL = "Uncategorized";

/** True when the category is inferred and the score is too weak to assert it. */
export function isUncategorized(type: EventType, confidence?: number): boolean {
  return (
    INFERRED_EVENTS.has(type) &&
    typeof confidence === "number" &&
    confidence < CATEGORY_CONFIDENCE_THRESHOLD
  );
}

export function eventLabel(type: EventType, confidence?: number): string {
  return isUncategorized(type, confidence) ? UNCATEGORIZED_LABEL : EVENT_LABELS[type];
}

export function eventShortLabel(type: EventType, confidence?: number): string {
  return isUncategorized(type, confidence)
    ? UNCATEGORIZED_SHORT_LABEL
    : EVENT_SHORT_LABELS[type];
}

export function momentTitle(moment: Moment): string {
  const semantic = moment.semanticTitle?.trim();
  if (semantic) return semantic;
  // A weak detection gets a neutral title too, rather than "Exciting moment" for
  // something the pipeline cannot show was exciting.
  if (isUncategorized(moment.eventType, moment.confidence)) return "Uncategorized moment";
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
