"use client";

import { cn } from "@/lib/cn";
import type {
  ConfidenceFilter,
  DateFilter,
  EventFilter,
  ModalityFilter,
} from "@/lib/filters";

const EVENT_OPTIONS: { id: EventFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "surprise", label: "Surprise" },
  { id: "insight", label: "Insight" },
  { id: "error", label: "Error" },
  { id: "load", label: "Load" },
];

export type SortMode = "time" | "intensity";

export function FilterBar({
  event,
  onEventChange,
  confidence,
  onConfidenceChange,
  modality,
  onModalityChange,
  date,
  onDateChange,
  sort,
  onSortChange,
  session,
  sessions,
  onSessionChange,
}: {
  event: EventFilter;
  onEventChange: (value: EventFilter) => void;
  confidence: ConfidenceFilter;
  onConfidenceChange: (value: ConfidenceFilter) => void;
  modality: ModalityFilter;
  onModalityChange: (value: ModalityFilter) => void;
  date: DateFilter;
  onDateChange: (value: DateFilter) => void;
  sort: SortMode;
  onSortChange: (value: SortMode) => void;
  session: string;
  sessions: string[];
  onSessionChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {EVENT_OPTIONS.map((option) => {
          const active = event === option.id;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onEventChange(option.id)}
              aria-pressed={active}
              className={cn(
                "px-3 py-1.5 text-[11px] tracking-[0.18em] uppercase",
                active
                  ? "bg-fg text-bg"
                  : "border border-line-strong text-fg-dim hover:text-fg",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3">
        <label className="flex items-center gap-2 text-[11px] tracking-[0.12em] uppercase text-fg-mute">
          Intensity
          <select
            value={confidence}
            onChange={(event) =>
              onConfidenceChange(event.target.value as ConfidenceFilter)
            }
            className="border border-line-strong bg-bg px-2 py-1 text-[11px] tracking-normal text-fg outline-none"
          >
            <option value="all">Any</option>
            <option value="critical">Critical · red · ≥ 85%</option>
            <option value="high">High · orange · 70–84%</option>
            <option value="moderate">Moderate · yellow · 55–69%</option>
            <option value="weak">Weak · green · &lt; 55%</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-[11px] tracking-[0.12em] uppercase text-fg-mute">
          Modality
          <select
            value={modality}
            onChange={(event) =>
              onModalityChange(event.target.value as ModalityFilter)
            }
            className="border border-line-strong bg-bg px-2 py-1 text-[11px] tracking-normal text-fg outline-none"
          >
            <option value="all">Any</option>
            <option value="eeg">EEG</option>
            <option value="video">Video</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-[11px] tracking-[0.12em] uppercase text-fg-mute">
          Date
          <select
            value={date}
            onChange={(event) => onDateChange(event.target.value as DateFilter)}
            className="border border-line-strong bg-bg px-2 py-1 text-[11px] tracking-normal text-fg outline-none"
          >
            <option value="all">Any</option>
            <option value="today">Today</option>
            <option value="recent">Last 48 hours</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-[11px] tracking-[0.12em] uppercase text-fg-mute">
          Session
          <select value={session} onChange={(event) => onSessionChange(event.target.value)}
            className="max-w-44 border border-line-strong bg-bg px-2 py-1 text-[11px] tracking-normal text-fg outline-none">
            <option value="all">Any session</option>
            {sessions.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-[11px] tracking-[0.12em] uppercase text-fg-mute">
          Order
          <select
            value={sort}
            onChange={(event) => onSortChange(event.target.value as SortMode)}
            className="border border-line-strong bg-bg px-2 py-1 text-[11px] tracking-normal text-fg outline-none"
          >
            <option value="time">Time · session order</option>
            <option value="intensity">Intensity · strongest first</option>
          </select>
        </label>
      </div>
    </div>
  );
}
