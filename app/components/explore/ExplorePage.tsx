"use client";

import { useMemo, useState } from "react";
import { FilterBar } from "@/components/explore/FilterBar";
import { MomentTable } from "@/components/explore/MomentTable";
import { SearchBar } from "@/components/explore/SearchBar";
import { useMoments } from "@/context/MomentsProvider";
import {
  matchesFilters,
  type ConfidenceFilter,
  type DateFilter,
  type EventFilter,
  type ModalityFilter,
} from "@/lib/filters";

export function ExplorePage() {
  const { visibleMoments } = useMoments();
  const [event, setEvent] = useState<EventFilter>("all");
  const [confidence, setConfidence] = useState<ConfidenceFilter>("all");
  const [modality, setModality] = useState<ModalityFilter>("all");
  const [date, setDate] = useState<DateFilter>("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      visibleMoments.filter((moment) =>
        matchesFilters(moment, { event, confidence, modality, date, query }),
      ),
    [confidence, date, event, modality, query, visibleMoments],
  );

  return (
    <main className="mx-auto max-w-6xl px-5 pb-24 pt-24 md:px-8">
      <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">
        MemoryPalace / Explore
      </p>
      <h1 className="mt-3 font-serif text-4xl">
        Your repository of captured moments.
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-fg-dim">
        Each row is a candidate cognitive transition and the context around it.
        Filter and open any moment to inspect the supporting evidence.
      </p>

      <div className="mt-10 grid gap-6 border-y border-line py-6 md:grid-cols-[1fr_280px] md:items-start">
        <FilterBar
          event={event}
          onEventChange={setEvent}
          confidence={confidence}
          onConfidenceChange={setConfidence}
          modality={modality}
          onModalityChange={setModality}
          date={date}
          onDateChange={setDate}
        />
        <SearchBar value={query} onChange={setQuery} />
      </div>

      <p className="py-4 font-mono text-[11px] text-fg-mute">
        {filtered.length} {filtered.length === 1 ? "moment" : "moments"}
      </p>
      <MomentTable moments={filtered} />
    </main>
  );
}
