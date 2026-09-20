"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { EEG_CHANNEL_NAMES, nextLiveSample } from "@/lib/signals";

const SAMPLE_RATE = 250;
const WINDOW_SECONDS = 4;
const CHANNELS = EEG_CHANNEL_NAMES.length;

export function EEGMonitor({ burstId = 0 }: { burstId?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pendingBurst = useRef(0);
  const selectedRef = useRef<Set<number>>(new Set(Array.from({ length: CHANNELS }, (_, i) => i)));
  const [selected, setSelected] = useState<number[]>(
    Array.from({ length: CHANNELS }, (_, index) => index),
  );

  useEffect(() => {
    if (burstId) pendingBurst.current = burstId;
  }, [burstId]);

  useEffect(() => {
    selectedRef.current = new Set(selected);
  }, [selected]);

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
    let handledBurst = 0;
    let burstSamplesLeft = 0;
    let burstTotal = 1;
    let markerIndex: number | null = null;

    const draw = (now: number) => {
      const dt = Math.min(now - last, 50);
      last = now;
      const samplesToAdd = Math.max(1, Math.round((dt / 1000) * SAMPLE_RATE));
      if (pendingBurst.current && pendingBurst.current !== handledBurst) {
        handledBurst = pendingBurst.current;
        burstTotal = Math.round(SAMPLE_RATE * 0.42);
        burstSamplesLeft = burstTotal;
        markerIndex = writeIndex;
      }

      for (let i = 0; i < samplesToAdd; i += 1) {
        timeSeconds += 1 / SAMPLE_RATE;
        const progress = burstSamplesLeft > 0 ? 1 - burstSamplesLeft / burstTotal : 0;
        const spike = burstSamplesLeft > 0
          ? Math.sin(progress * Math.PI * 4) * Math.exp(-progress * 3) * 115
          : 0;
        for (let channel = 0; channel < CHANNELS; channel += 1) {
          buffers[channel][writeIndex] = nextLiveSample(channel, timeSeconds)
            + (selectedRef.current.has(channel) ? spike : 0);
        }
        if (burstSamplesLeft > 0) burstSamplesLeft -= 1;
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

      const left = 48;
      const plotWidth = width - left - 12;
      const rowHeight = height / CHANNELS;
      const length = buffers[0].length;

      buffers.forEach((buffer, channel) => {
        const mid = rowHeight * channel + rowHeight / 2;
        ctx.beginPath();
        for (let i = 0; i < length; i += 2) {
          const sample = buffer[(writeIndex + i) % length];
          const x = left + (i / (length - 1)) * plotWidth;
          const y = mid - (sample / 120) * (rowHeight * 0.42);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = selectedRef.current.has(channel)
          ? "rgba(201, 184, 150, 0.86)" : "rgba(109, 104, 96, 0.42)";
        ctx.lineWidth = selectedRef.current.has(channel) ? 1.15 : 0.8;
        ctx.stroke();
        ctx.fillStyle = selectedRef.current.has(channel)
          ? "rgba(201, 184, 150, 0.95)" : "rgba(109, 104, 96, 0.8)";
        ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillText(EEG_CHANNEL_NAMES[channel], 8, mid + 4);
      });

      if (markerIndex !== null) {
        const offset = (markerIndex - writeIndex + length) % length;
        const markerX = left + (offset / (length - 1)) * plotWidth;
        ctx.strokeStyle = "rgba(196, 132, 116, .9)";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(markerX, 0);
        ctx.lineTo(markerX, height);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(196, 132, 116, .95)";
        ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillText("SPIKE", Math.min(markerX + 5, width - 42), 13);
      }
      frame = requestAnimationFrame(draw);
    };

    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, []);

  const toggle = (index: number) => {
    setSelected((current) => current.includes(index)
      ? current.filter((item) => item !== index)
      : [...current, index]);
  };

  return (
    <section className="flex h-full min-h-[420px] flex-col overflow-hidden rounded-[28px] border border-line bg-bg-panel/85 shadow-2xl">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-4">
        <div>
          <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">8-channel EEG</h2>
          <p className="mt-1 font-mono text-[11px] text-fg-mute">250 Hz · simulated stream</p>
        </div>
        <span className="font-mono text-[10px] tracking-[0.16em] uppercase text-ok">● Incoming</span>
      </header>
      <div className="flex flex-wrap gap-1.5 border-b border-line px-4 py-3">
        {EEG_CHANNEL_NAMES.map((name, index) => (
          <button key={name} type="button" aria-pressed={selected.includes(index)}
            onClick={() => toggle(index)}
            className={cn("rounded-full border px-2.5 py-1 font-mono text-[10px] transition",
              selected.includes(index) ? "border-accent/35 bg-accent/10 text-accent" : "border-white/10 text-fg-mute")}>
            {name}
          </button>
        ))}
        <button type="button" onClick={() => setSelected(Array.from({ length: CHANNELS }, (_, i) => i))}
          className="ml-auto px-2 text-[10px] uppercase tracking-[0.12em] text-fg-mute hover:text-fg">
          Select all
        </button>
      </div>
      <canvas ref={canvasRef} className="min-h-[320px] flex-1 w-full" role="img"
        aria-label="Live eight-channel EEG monitor with highlighted simulated neural spike" />
    </section>
  );
}
