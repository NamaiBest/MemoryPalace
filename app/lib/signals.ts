import type { EEGInfo } from "@/types/moment";

export const EEG_CHANNEL_NAMES = [
  "CP3",
  "C3",
  "F5",
  "PO3",
  "PO4",
  "F6",
  "C4",
  "CP4",
] as const;

function mulberry32(seed: number): () => number {
  let state = seed;
  return () => {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function generateEEG(
  seed: number,
  samples = 500,
  sampleRateHz = 250,
): EEGInfo {
  const rand = mulberry32(seed);
  const eventMarkerIndex = Math.floor(samples * 0.5);
  const windowRadius = Math.floor(sampleRateHz * 0.5);

  const traces = EEG_CHANNEL_NAMES.map((_, channel) => {
    const phase = rand() * Math.PI * 2;
    const alpha = 8 + channel * 0.35;
    const beta = 18 + channel * 0.6;
    const amplitude = 22 + rand() * 16;
    const burstAmp = 12 + channel * 1.4 + rand() * 6;
    const values: number[] = [];

    for (let i = 0; i < samples; i += 1) {
      const t = i / sampleRateHz;
      const envelope = Math.exp(
        -((i - eventMarkerIndex) ** 2) / (2 * 18 ** 2),
      );
      const noise = (rand() - 0.5) * 7;
      const signal =
        amplitude *
          (0.62 * Math.sin(2 * Math.PI * alpha * t + phase) +
            0.28 * Math.sin(2 * Math.PI * beta * t + phase * 0.4)) +
        burstAmp * envelope +
        noise;
      values.push(signal);
    }

    return values;
  });

  return {
    channelCount: EEG_CHANNEL_NAMES.length,
    sampleRateHz,
    windowSeconds: 2,
    channelNames: [...EEG_CHANNEL_NAMES],
    traces,
    eventMarkerIndex,
    windowStartIndex: Math.max(0, eventMarkerIndex - windowRadius),
    windowEndIndex: Math.min(samples - 1, eventMarkerIndex + windowRadius),
  };
}

export function nextLiveSample(
  channel: number,
  timeSeconds: number,
  burst = 0,
  rand = Math.random,
): number {
  const alpha = 9 + channel * 0.4;
  const beta = 17 + channel * 0.55;
  const base =
    18 * Math.sin(2 * Math.PI * alpha * timeSeconds + channel) +
    8 * Math.sin(2 * Math.PI * beta * timeSeconds + channel * 0.5) +
    (rand() - 0.5) * 6;
  return base + burst * (10 + channel);
}
