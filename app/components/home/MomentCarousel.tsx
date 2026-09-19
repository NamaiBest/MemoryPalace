"use client";

import { useEffect, useRef } from "react";
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

  useEffect(() => {
    const selected = rowRef.current?.querySelector<HTMLElement>(
      `[aria-pressed="true"]`,
    );
    selected?.scrollIntoView({
      inline: "center",
      block: "nearest",
      behavior: "smooth",
    });
  }, [selectedId]);

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-10 bg-gradient-to-r from-bg to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-gradient-to-l from-bg to-transparent" />
      <div
        ref={rowRef}
        className="scrollbar-none flex gap-3 overflow-x-auto px-5 pb-1 md:px-8"
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
    </div>
  );
}
