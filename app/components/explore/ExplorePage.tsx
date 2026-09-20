"use client";

import { useEffect, useMemo, useState } from "react";
import { FilterBar, type SortMode } from "@/components/explore/FilterBar";
import { MomentTable } from "@/components/explore/MomentTable";
import { SearchBar } from "@/components/explore/SearchBar";
import { SessionTimeline } from "@/components/explore/SessionTimeline";
import { useMoments } from "@/context/MomentsProvider";
import {
  matchesFilters,
  type ConfidenceFilter,
  type DateFilter,
  type EventFilter,
  type ModalityFilter,
} from "@/lib/filters";
import type { Moment } from "@/types/moment";

export function ExplorePage() {
  const { visibleMoments } = useMoments();
  const [event, setEvent] = useState<EventFilter>("all");
  const [confidence, setConfidence] = useState<ConfidenceFilter>("all");
  const [modality, setModality] = useState<ModalityFilter>("all");
  const [date, setDate] = useState<DateFilter>("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("time");
  const [session, setSession] = useState("all");
  const [semanticResults, setSemanticResults] = useState<Moment[] | null>(null);
  const [searchState, setSearchState] = useState<
    "idle" | "searching" | "elastic" | "local"
  >("idle");

  useEffect(() => {
    const value = query.trim();
    const hasRemoteCriteria = Boolean(value || event !== "all" || confidence !== "all"
      || date !== "all" || session !== "all" || sort !== "time");
    if (!hasRemoteCriteria) {
      const reset = window.setTimeout(() => {
        setSemanticResults(null);
        setSearchState("idle");
      }, 0);
      return () => window.clearTimeout(reset);
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      try {
        const params = new URLSearchParams({ q: value });
        if (event !== "all") params.set("event_type", event);
        const ranges: Record<Exclude<ConfidenceFilter, "all">, [number, number]> = {
          critical: [0.85, 1],
          high: [0.7, 0.849999],
          moderate: [0.55, 0.699999],
          weak: [0, 0.549999],
        };
        if (confidence !== "all") {
          const [minimum, maximum] = ranges[confidence];
          params.set("min_intensity", String(minimum));
          params.set("max_intensity", String(maximum));
        }
        if (session !== "all") params.set("session_id", session);
        if (date === "recent") {
          params.set("date_from", new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString());
        } else if (date === "today") {
          const start = new Date();
          start.setHours(0, 0, 0, 0);
          params.set("date_from", start.toISOString());
        }
        params.set("sort", sort);
        const response = await fetch(`/api/search?${params.toString()}`, {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error("Elastic unavailable");
        const body = (await response.json()) as { moments?: Moment[] };
        setSemanticResults(body.moments ?? []);
        setSearchState("elastic");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setSemanticResults(null);
        setSearchState("local");
      }
    }, 320);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [confidence, date, event, query, session, sort]);

  const filtered = useMemo(
    () => {
      const moments = semanticResults ?? visibleMoments;
      const matches = moments.filter((moment) =>
        matchesFilters(moment, {
          event,
          confidence,
          modality,
          date,
          session,
          query: semanticResults ? "" : query,
        }),
      );
      return [...matches].sort((a, b) =>
        sort === "intensity"
          ? b.confidence - a.confidence
          : new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );
    },
    [confidence, date, event, modality, query, semanticResults, session, sort, visibleMoments],
  );

  const sessions = useMemo(() => Array.from(new Set(
    visibleMoments.map((moment) => moment.sessionId).filter(Boolean) as string[],
  )).sort(), [visibleMoments]);

  return (
    <main className="mx-auto max-w-[1500px] px-6 pb-24 pt-36 md:px-12">
      <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">
        MemoryPalace / Explore
      </p>
      <h1 className="mt-4 font-serif text-5xl md:text-6xl">
        Your collection.
      </h1>
      <p className="mt-5 max-w-2xl text-base leading-8 text-fg-dim">
        Find a moment, revisit the details, and keep what matters to you.
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
          sort={sort}
          onSortChange={setSort}
          session={session}
          sessions={sessions}
          onSessionChange={setSession}
        />
        <div>
          <SearchBar
            value={query}
            onChange={(value) => {
              setQuery(value);
              setSemanticResults(null);
              setSearchState(value.trim() ? "searching" : "idle");
            }}
          />
          <p className="mt-2 font-mono text-[10px] leading-5 tracking-[0.08em] text-fg-mute">
            {searchState === "elastic" && "ELASTIC · JINA V5 OMNI · HYBRID RRF"}
            {searchState === "searching" && "SEARCHING COGNITIVE MEMORY…"}
            {searchState === "local" && "LOCAL TEXT FALLBACK · ELASTIC OFFLINE"}
            {searchState === "idle" && "SEMANTIC + KEYWORD MEMORY SEARCH"}
          </p>
        </div>
      </div>

      <SessionTimeline moments={filtered} sessionMoments={visibleMoments} />

      <p className="py-5 font-mono text-[11px] text-fg-mute">
        {filtered.length} {filtered.length === 1 ? "moment" : "moments"}
      </p>
      <MomentTable moments={filtered} />
    </main>
  );
}
