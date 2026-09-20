"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { MomentCard } from "@/components/home/MomentCard";
import type { Moment } from "@/types/moment";

export function MomentCarousel({
  moments,
  selectedId,
  onSelect,
}: {
  moments: Moment[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [canPrevious, setCanPrevious] = useState(false);
  const [canNext, setCanNext] = useState(false);

  useEffect(() => {
    const row = rowRef.current;
    if (!row) return;
    const update = () => {
      setCanPrevious(row.scrollLeft > 4);
      setCanNext(row.scrollLeft + row.clientWidth < row.scrollWidth - 4);
    };
    const observer = new ResizeObserver(update);
    observer.observe(row);
    row.addEventListener("scroll", update, { passive: true });
    update();
    return () => { observer.disconnect(); row.removeEventListener("scroll", update); };
  }, [moments.length]);

  useEffect(() => {
    const selected = rowRef.current?.querySelector<HTMLElement>(
      `[aria-pressed="true"]`,
    );
    const row = rowRef.current;
    if (row && selected) {
      row.scrollTo({
        left: Math.max(0, row.scrollLeft + selected.getBoundingClientRect().left
          - row.getBoundingClientRect().left - (row.clientWidth - selected.clientWidth) / 2),
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
      });
    }
  }, [selectedId]);

  return (
    <section className="relative" aria-label="Your moment collection">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4 px-6 md:px-12">
        <div className="flex items-baseline gap-4">
          <h2 className="font-serif text-2xl md:text-3xl">Your moments</h2>
          <span className="text-sm text-fg-dim">{moments.length} saved</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/explore" className="mr-2 text-sm text-accent hover:text-fg">View all →</Link>
          {([-1, 1] as const).map((direction) => (
            <button type="button" key={direction} aria-label={direction < 0 ? "Previous moments" : "Next moments"}
              disabled={direction < 0 ? !canPrevious : !canNext}
              onClick={() => rowRef.current?.scrollBy({ left: direction * rowRef.current.clientWidth * 0.8,
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" })}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-line-strong bg-bg/40 text-lg backdrop-blur-md transition hover:border-accent disabled:cursor-default disabled:opacity-25">
              <span aria-hidden>{direction < 0 ? "←" : "→"}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-10 bg-gradient-to-r from-bg to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-gradient-to-l from-bg to-transparent" />
      <div
        ref={rowRef}
        className="scrollbar-none flex snap-x snap-mandatory scroll-px-6 gap-5 overflow-x-auto px-6 py-4 md:scroll-px-12 md:gap-6 md:px-12"
      >
        {moments.map((moment) => (
          <MomentCard
            key={moment.id}
            moment={moment}
            selected={moment.id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </section>
  );
}
