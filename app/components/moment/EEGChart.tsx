"use client";

import { useEffect, useRef } from "react";
import type { EEGInfo } from "@/types/moment";

function draw(canvas: HTMLCanvasElement, eeg: EEGInfo) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const left = 48;
  const right = 16;
  const top = 10;
  const bottom = 28;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const rowHeight = plotHeight / eeg.channelCount;
  const samples = eeg.traces[0]?.length ?? 0;

  const windowX1 =
    left + (eeg.windowStartIndex / Math.max(samples - 1, 1)) * plotWidth;
  const windowX2 =
    left + (eeg.windowEndIndex / Math.max(samples - 1, 1)) * plotWidth;
  const markerX =
    left + (eeg.eventMarkerIndex / Math.max(samples - 1, 1)) * plotWidth;

  ctx.fillStyle = "rgba(201, 184, 150, 0.08)";
  ctx.fillRect(windowX1, top, windowX2 - windowX1, plotHeight);

  ctx.strokeStyle = "rgba(201, 184, 150, 0.55)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(markerX, top);
  ctx.lineTo(markerX, top + plotHeight);
  ctx.stroke();
  ctx.setLineDash([]);

  eeg.traces.forEach((trace, index) => {
    const mid = top + rowHeight * index + rowHeight / 2;
    const peak = Math.max(...trace.map((value) => Math.abs(value)), 1);
    ctx.beginPath();
    trace.forEach((value, sample) => {
      const x = left + (sample / Math.max(samples - 1, 1)) * plotWidth;
      const y = mid - (value / peak) * (rowHeight * 0.38);
      if (sample === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "rgba(243, 239, 230, 0.72)";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = "rgba(156, 150, 139, 0.95)";
    ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.fillText(eeg.channelNames[index] ?? `Ch ${index + 1}`, 8, mid + 4);
  });

  ctx.fillStyle = "rgba(109, 104, 96, 1)";
  ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
  ctx.fillText("−1.0 s", left, height - 8);
  ctx.fillText("event", markerX - 14, height - 8);
  ctx.fillText("+1.0 s", width - right - 40, height - 8);
  ctx.fillText("µV", 8, 14);
}

export function EEGChart({ eeg }: { eeg: EEGInfo }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const render = () => draw(canvas, eeg);
    render();
    const observer = new ResizeObserver(render);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [eeg]);

  return (
    <section className="border border-line bg-bg-panel p-5 md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">
            Event-associated EEG window
          </h2>
          <p className="mt-2 text-sm text-fg-mute">
            Simulated 8-channel waveform around the candidate transition. This
            display does not identify a thought or memory.
          </p>
        </div>
        <p className="font-mono text-[11px] text-fg-dim">
          {eeg.channelCount} channels · {eeg.sampleRateHz} Hz · {eeg.windowSeconds}s
          analysis window
        </p>
      </div>
      <canvas
        ref={canvasRef}
        className="mt-5 h-[320px] w-full md:h-[380px]"
        role="img"
        aria-label="Eight-channel EEG traces with an event marker and selected analysis window"
      />
      <p className="mt-3 font-mono text-[10px] tracking-[0.12em] uppercase text-fg-mute">
        Shaded region: selected event window · dashed line: candidate event
      </p>
    </section>
  );
}
