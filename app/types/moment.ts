// "load" is what the detector actually measures: sustained elevated cognitive load
// against this session's own baseline. The other three describe simulated moments and
// are not something the current pipeline can distinguish.
export type EventType = "capture" | "surprise" | "excitement" | "insight" | "error" | "load";

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
  recordingId?: string;
  sessionId?: string;
  userId?: string;
  demo?: boolean;
  sequence: number;
  timestamp: string;
  eventType: EventType;
  confidence: number;
  spikeIntensity?: number;
  spikeConfidence?: number;
  media: MomentMedia;
  eeg?: EEGInfo;
  contextWindow: ContextWindow;
  annotation: string;
  status: MomentStatus;
  summary: string;
  semanticTitle?: string;
  aiDescription?: string;
  keywords?: string[];
  topics?: string[];
  transcript?: string;
  processing?: {
    extraction: "pending" | "complete" | "failed" | "not_configured";
    analysis?: "pending" | "complete" | "failed" | "not_configured";
    indexing: "pending" | "complete" | "failed" | "not_configured";
  };
  vision?: {
    provider: "meta";
    model: string;
    status: "complete" | "failed";
    source?: "video" | "poster";
    error?: string;
  };
}
