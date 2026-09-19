"use client";

import { useEffect, useRef } from "react";
import { EEG_CHANNEL_NAMES, nextLiveSample } from "@/lib/signals";

const SAMPLE_RATE = 250;
const WINDOW_SECONDS = 4;
const CHANNELS = EEG_CHANNEL_NAMES.length;

export function EEGMonitor({ burst = 0 }: { burst?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const burstRef = useRef(burst);

  useEffect(() => {
    burstRef.current = burst;
  }, [burst]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const buffers = Array.from({ length: CHANNELS }, () =>
      new Float32Array(SAMPLE_RATE * WINDOW_SECONDS),
    );
    let writeIndex = 0;
    let timeSeconds = 0;
    let last = performance.now();
    let frame = 0;

    const draw = (now: number) => {
      const dt = Math.min(now - last, 50);
      last = now;
      const samplesToAdd = Math.max(1, Math.round((dt / 1000) * SAMPLE_RATE));
      const burstValue = burstRef.current;

      for (let i = 0; i < samplesToAdd; i += 1) {
        timeSeconds += 1 / SAMPLE_RATE;
        for (let channel = 0; channel < CHANNELS; channel += 1) {
          buffers[channel][writeIndex] = nextLiveSample(
            channel,
            timeSeconds,
            burstValue,
          );
        }
        writeIndex = (writeIndex + 1) % buffers[0].length;
      }

      const ctx = canvas.getContext("2d");
      if (!ctx) {
        frame = requestAnimationFrame(draw);
        return;
      }

      const dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "#101011";
      ctx.fillRect(0, 0, width, height);

      const left = 44;
      const plotWidth = width - left - 12;
      const rowHeight = height / CHANNELS;
      const length = buffers[0].length;

      buffers.forEach((buffer, channel) => {
        const mid = rowHeight * channel + rowHeight / 2;
        ctx.beginPath();
        for (let i = 0; i < length; i += 2) {
          const sample = buffer[(writeIndex + i) % length];
          const x = left + (i / (length - 1)) * plotWidth;
          const y = mid - (sample / 48) * (rowHeight * 0.36);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = "rgba(201, 184, 150, 0.78)";
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = "rgba(156, 150, 139, 0.95)";
        ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillText(EEG_CHANNEL_NAMES[channel], 8, mid + 4);
      });

      frame = requestAnimationFrame(draw);
    };

    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <section className="flex h-full min-h-[320px] flex-col border border-line bg-bg-panel">
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <div>
          <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">
            8-channel EEG
          </h2>
          <p className="mt-1 font-mono text-[11px] text-fg-mute">
            250 Hz · simulated stream
          </p>
        </div>
        <span className="font-mono text-[10px] tracking-[0.16em] uppercase text-ok">
          Incoming
        </span>
      </header>
      <canvas
        ref={canvasRef}
        className="min-h-[280px] flex-1 w-full"
        role="img"
        aria-label="Live eight-channel EEG monitor"
      />
    </section>
  );
}
