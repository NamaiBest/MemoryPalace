"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { HeroMoment } from "@/components/home/HeroMoment";
import { MomentCarousel } from "@/components/home/MomentCarousel";
import { MediaBackdrop } from "@/components/media/MediaBackdrop";
import { useMoments } from "@/context/MomentsProvider";
import { formatDateKey } from "@/lib/format";

export function HomePage() {
  const { visibleMoments, lastCreatedId, selectedDate, setSelectedDate } = useMoments();
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
      <main className="relative flex min-h-dvh items-center overflow-hidden px-6 pb-20 pt-36 md:px-12">
        <div aria-hidden className="pointer-events-none absolute right-[-10%] top-[10%] h-[65vh] w-[70vw] rounded-full bg-accent/10 blur-[120px]" />
        <div aria-hidden className="pointer-events-none absolute bottom-0 left-0 h-[35vh] w-[50vw] rounded-full bg-insight/10 blur-[100px]" />
        <div className="relative mx-auto w-full max-w-[1404px]">
          <p className="text-xs tracking-[0.2em] uppercase text-accent">Your personal collection</p>
          <h1 className="mt-7 max-w-3xl text-balance font-serif text-5xl leading-[1.12] md:text-7xl">
            {selectedDate ? `No moments on ${formatDateKey(selectedDate)}.` : "Some moments deserve a second look."}
          </h1>
          <p className="mt-7 max-w-lg text-base leading-8 text-fg-dim">
            {selectedDate
              ? "Choose another day or return to the complete collection. Your saved memories have not been removed."
              : "Capture a little of your day. Your moments will be waiting here, ready to watch, remember, and make your own."}
          </p>
          <div className="mt-9 flex flex-wrap gap-4">
            {selectedDate ? (
              <button type="button" onClick={() => setSelectedDate(null)}
                className="inline-flex rounded-xl bg-accent px-7 py-3.5 text-sm font-medium text-bg transition-colors hover:bg-fg">
                Show all dates
              </button>
            ) : (
              <Link
                href="/live"
                className="inline-flex rounded-xl bg-accent px-7 py-3.5 text-sm font-medium text-bg transition-colors hover:bg-fg"
              >
                Capture your first moment →
              </Link>
            )}
            <Link
              href="/debug"
              className="inline-flex rounded-xl border border-line-strong bg-white/5 px-6 py-3.5 text-sm text-fg-dim backdrop-blur-md transition-colors hover:text-fg"
            >
              Check connection
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-dvh flex-col overflow-hidden">
      <MediaBackdrop moment={selected} />
      <div className="relative flex min-h-dvh flex-col justify-end">
        <HeroMoment moment={selected} />
        <div className="bg-gradient-to-t from-bg via-bg/60 to-transparent pb-8 md:pb-10">
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
