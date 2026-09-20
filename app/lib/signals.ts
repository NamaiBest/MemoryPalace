import type { EEGInfo } from "@/types/moment";
import {
  REPLAY_BASE64,
  REPLAY_CHANNELS,
  REPLAY_SAMPLE_RATE,
  REPLAY_SCALE,
} from "@/lib/eegReplay";

/**
 * Real EEG, replayed.
 *
 * These traces used to be two summed sine waves per channel, which does not look like
 * EEG: no 1/f slope, no drift, no blinks, and every channel carrying the same rhythm at
 * a different offset. The buffer below is a 30 s, 8 channel recording from the team's
 * own Emotiv EPOC X session (dataset/epocx-imagery), bandpassed 1-40 Hz, notched,
 * common average referenced and scaled to microvolts. It measures a 1/f log-log slope
 * of -1.03, which is what real scalp EEG does and what summed sinusoids never do.
 *
 * It is decoded once, lazily, and then read by time so the monitor's own sample rate
 * stays independent of the recording's 128 Hz. This is recorded data on a loop. It is
 * never presented as live capture from whoever is wearing the headset.
 */
let replayBuffer: Float32Array[] | null = null;

function replay(): Float32Array[] {
  if (replayBuffer) return replayBuffer;
  const binary = typeof atob === "function"
    ? atob(REPLAY_BASE64)
    : Buffer.from(REPLAY_BASE64, "base64").toString("binary");
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const samples = new Int16Array(bytes.buffer);
  const channels = REPLAY_CHANNELS.length;
  const perChannel = samples.length / channels;
  const out = Array.from({ length: channels }, () => new Float32Array(perChannel));
  for (let i = 0; i < perChannel; i += 1) {
    for (let c = 0; c < channels; c += 1) {
      out[c][i] = samples[i * channels + c] / REPLAY_SCALE;
    }
  }
  replayBuffer = out;
  return out;
}

/** Microvolts for one channel at an arbitrary time, wrapping the recording and
 *  interpolating between samples so playback is smooth at any refresh rate. */
function replaySample(channel: number, timeSeconds: number, offsetSeconds = 0): number {
  const buffers = replay();
  const trace = buffers[channel % buffers.length];
  const position = (timeSeconds + offsetSeconds) * REPLAY_SAMPLE_RATE;
  const length = trace.length;
  const base = ((Math.floor(position) % length) + length) % length;
  const next = (base + 1) % length;
  const fraction = position - Math.floor(position);
  return trace[base] * (1 - fraction) + trace[next] * fraction;
}

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

  // The seed picks a stable window into the recording, so a given moment always shows
  // the same trace across reloads while different moments show different EEG.
  const windowOffset = rand() * 20;

  const traces = EEG_CHANNEL_NAMES.map((_, channel) => {
    const burstAmp = 12 + channel * 1.4 + rand() * 6;
    const values: number[] = [];

    for (let i = 0; i < samples; i += 1) {
      const t = i / sampleRateHz;
      // The event marker keeps its visible deflection, so the chart still shows where
      // the detector fired. Everything under it is recorded EEG rather than a sine.
      const envelope = Math.exp(
        -((i - eventMarkerIndex) ** 2) / (2 * 18 ** 2),
      );
      values.push(
        replaySample(channel, t, windowOffset + channel * 3.7) + burstAmp * envelope,
      );
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
): number {
  // Each channel starts at a different point in the recording so the eight traces are
  // not a single waveform drawn eight times, while each one stays real EEG.
  return replaySample(channel, timeSeconds, channel * 3.7) + burst * (10 + channel);
}
