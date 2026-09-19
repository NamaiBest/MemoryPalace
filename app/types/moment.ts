// "load" is what the detector actually measures: sustained elevated cognitive load
// against this session's own baseline. The other three describe simulated moments and
// are not something the current pipeline can distinguish.
export type EventType = "surprise" | "insight" | "error" | "load";

export type MomentStatus = "candidate" | "kept" | "deleted";

export type Modality = "eeg" | "video";

export interface ContextWindow {
  start: string;
  end: string;
}

export interface EEGInfo {
  channelCount: number;
  sampleRateHz: number;
  windowSeconds: number;
  channelNames: string[];
  traces: number[][];
  eventMarkerIndex: number;
  windowStartIndex: number;
  windowEndIndex: number;
}

export interface MomentMedia {
  thumbnailUrl: string;
  videoUrl?: string;
  alt: string;
}

export interface Moment {
  id: string;
  sequence: number;
  timestamp: string;
  eventType: EventType;
  confidence: number;
  media: MomentMedia;
  eeg?: EEGInfo;
  contextWindow: ContextWindow;
  annotation: string;
  status: MomentStatus;
  summary: string;
}
