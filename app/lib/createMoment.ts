import { MEDIA } from "@/data/media";
import { generateEEG } from "@/lib/signals";
import type { EventType, Moment, MomentMedia, MomentStatus } from "@/types/moment";

const DEFAULT_MEDIA: MomentMedia[] = [
  MEDIA.desk,
  MEDIA.city,
  MEDIA.night,
  MEDIA.study,
  MEDIA.train,
  MEDIA.cafe,
];

function offsetIso(iso: string, seconds: number): string {
  return new Date(new Date(iso).getTime() + seconds * 1000).toISOString();
}

export function buildMoment(input: {
  sequence: number;
  timestamp: string;
  eventType: EventType;
  confidence: number;
  media: MomentMedia;
  summary: string;
  annotation?: string;
  status?: MomentStatus;
  includeEEG?: boolean;
  contextPaddingSeconds?: number;
}): Moment {
  const includeEEG = input.includeEEG ?? true;
  const padding = input.contextPaddingSeconds ?? 60;

  return {
    id: `moment-${String(input.sequence).padStart(3, "0")}`,
    sequence: input.sequence,
    timestamp: input.timestamp,
    eventType: input.eventType,
    confidence: input.confidence,
    media: input.media,
    eeg: includeEEG ? generateEEG(input.sequence * 97) : undefined,
    contextWindow: {
      start: offsetIso(input.timestamp, -padding),
      end: offsetIso(input.timestamp, padding),
    },
    annotation: input.annotation ?? "",
    status: input.status ?? "candidate",
    summary: input.summary,
  };
}

export function createSimulatedMoment(
  eventType: EventType,
  sequence: number,
  timestamp = new Date().toISOString(),
): Moment {
  const media = DEFAULT_MEDIA[sequence % DEFAULT_MEDIA.length];
  const summaries: Record<EventType, string> = {
    surprise: "A candidate cognitive transition during the live monitoring session.",
    insight: "A candidate cognitive transition during focused work in the live session.",
    error: "A candidate error-related event captured during the live session.",
    load: "Sustained elevated load measured against this session's baseline.",
  };

  return buildMoment({
    sequence,
    timestamp,
    eventType,
    confidence: eventType === "surprise" ? 0.86 : eventType === "insight" ? 0.81 : 0.74,
    media,
    summary: summaries[eventType],
    annotation: "",
    status: "candidate",
    includeEEG: true,
    contextPaddingSeconds: 60,
  });
}
