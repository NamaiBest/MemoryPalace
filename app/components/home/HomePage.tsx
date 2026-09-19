"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { HeroMoment } from "@/components/home/HeroMoment";
import { MomentCarousel } from "@/components/home/MomentCarousel";
import { MediaBackdrop } from "@/components/media/MediaBackdrop";
import { useMoments } from "@/context/MomentsProvider";

export function HomePage() {
  const { visibleMoments, lastCreatedId } = useMoments();
  const [selectedId, setSelectedId] = useState(
    lastCreatedId ?? visibleMoments[0]?.id ?? "",
  );
  const [seenCreatedId, setSeenCreatedId] = useState(lastCreatedId);

  if (lastCreatedId && lastCreatedId !== seenCreatedId) {
    setSeenCreatedId(lastCreatedId);
    setSelectedId(lastCreatedId);
  }

  const selectedExists = visibleMoments.some((moment) => moment.id === selectedId);
  if (!selectedExists && visibleMoments[0] && selectedId !== visibleMoments[0].id) {
    setSelectedId(visibleMoments[0].id);
  }

  const selected = useMemo(
    () => visibleMoments.find((moment) => moment.id === selectedId) ?? visibleMoments[0],
    [selectedId, visibleMoments],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!selected || event.target instanceof HTMLInputElement) return;
      const index = visibleMoments.findIndex((moment) => moment.id === selected.id);
      if (event.key === "ArrowRight") {
        const next = visibleMoments[Math.min(visibleMoments.length - 1, index + 1)];
        if (next) setSelectedId(next.id);
      }
      if (event.key === "ArrowLeft") {
        const prev = visibleMoments[Math.max(0, index - 1)];
        if (prev) setSelectedId(prev.id);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selected, visibleMoments]);

  if (!selected) {
    return (
      <main className="flex min-h-dvh items-center justify-center px-6 pt-16">
        <div className="max-w-md text-center">
          <p className="font-serif text-3xl">No moments yet</p>
          <p className="mt-3 text-sm leading-6 text-fg-dim">
            Every moment here comes from a real recording: the detector stops a clip, the
            phone uploads it, and it appears within a few seconds. Nothing is seeded, so an
            empty gallery means no capture has happened yet.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/debug"
              className="inline-flex border border-accent/50 px-5 py-2.5 text-[11px] tracking-[0.22em] uppercase text-accent transition-colors hover:bg-accent hover:text-bg"
            >
              Check the connection
            </Link>
            <Link
              href="/live"
              className="inline-flex border border-line-strong px-5 py-2.5 text-[11px] tracking-[0.22em] uppercase text-fg-dim transition-colors hover:text-fg"
            >
              Open Live
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-dvh flex-col overflow-hidden md:h-dvh">
      <MediaBackdrop moment={selected} />
      <div className="relative flex min-h-dvh flex-col justify-end">
        <HeroMoment moment={selected} />
        <div className="pb-6 md:pb-8">
          <MomentCarousel
            moments={visibleMoments}
            selectedId={selected.id}
            onSelect={setSelectedId}
          />
        </div>
      </div>
    </main>
  );
}
