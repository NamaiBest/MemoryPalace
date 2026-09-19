"use client";

import { useEffect, useState } from "react";
import { MEDIA } from "@/data/media";
import { resolveCameraSource } from "@/lib/integrations";
import { cn } from "@/lib/cn";

const SCENES = [MEDIA.desk, MEDIA.city, MEDIA.cafe, MEDIA.study, MEDIA.night];

export function CameraFeed({ capturing = false }: { capturing?: boolean }) {
  const source = resolveCameraSource();
  const [index, setIndex] = useState(0);
  const [clock, setClock] = useState(() => new Date());

  useEffect(() => {
    const sceneTimer = window.setInterval(() => {
      setIndex((current) => (current + 1) % SCENES.length);
    }, 7000);
    const clockTimer = window.setInterval(() => setClock(new Date()), 1000);
    return () => {
      window.clearInterval(sceneTimer);
      window.clearInterval(clockTimer);
    };
  }, []);

  const scene = SCENES[index];

  return (
    <section className="relative flex min-h-[320px] flex-col overflow-hidden border border-line bg-black">
      <header className="absolute inset-x-0 top-0 z-10 flex items-center justify-between px-4 py-3">
        <p className="text-[11px] tracking-[0.2em] uppercase text-fg">
          POV camera
        </p>
        <p className="font-mono text-[10px] tracking-[0.14em] uppercase text-fg-dim">
          {source.label}
        </p>
      </header>

      {source.kind === "stream" && source.url ? (
        <video
          src={source.url}
          autoPlay
          muted
          playsInline
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            key={scene.thumbnailUrl}
            src={scene.thumbnailUrl}
            alt=""
            className="absolute inset-0 h-full w-full object-cover kenburns"
          />
          <div className="absolute inset-0 bg-black/25" />
        </>
      )}

      <div
        className={cn(
          "pointer-events-none absolute inset-0 border-2 transition-colors",
          capturing ? "border-accent/80" : "border-white/15",
        )}
      />
      <div className="pointer-events-none absolute left-3 top-12 h-6 w-6 border-l border-t border-white/50" />
      <div className="pointer-events-none absolute right-3 top-12 h-6 w-6 border-r border-t border-white/50" />
      <div className="pointer-events-none absolute bottom-3 left-3 h-6 w-6 border-b border-l border-white/50" />
      <div className="pointer-events-none absolute bottom-3 right-3 h-6 w-6 border-b border-r border-white/50" />
      <div className="grain absolute inset-0" />

      <div className="absolute inset-x-0 bottom-0 z-10 flex items-center justify-between px-4 py-3">
        <span className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.16em] uppercase text-error">
          <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-error" />
          Rec · simulated
        </span>
        <span className="font-mono text-[11px] text-fg-dim">
          {clock.toLocaleTimeString("en-US", { hour12: false })}
        </span>
      </div>
    </section>
  );
}
