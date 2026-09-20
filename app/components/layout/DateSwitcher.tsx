"use client";

import { formatDateKey } from "@/lib/format";
import { useMoments } from "@/context/MomentsProvider";

export function DateSwitcher() {
  const { availableDates, selectedDate, setSelectedDate } = useMoments();

  return (
    <label className="group relative flex min-w-[154px] items-center gap-2 rounded-full border border-white/10 bg-white/[.045] px-3.5 py-2 text-fg-dim backdrop-blur-xl transition hover:border-accent/35 hover:text-fg">
      <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-accent" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M6.5 3.5v3M17.5 3.5v3M4 9h16M5.5 5h13A1.5 1.5 0 0 1 20 6.5v12a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5v-12A1.5 1.5 0 0 1 5.5 5Z" />
      </svg>
      <span className="sr-only">Filter memories by date</span>
      <select
        value={selectedDate ?? "all"}
        onChange={(event) => setSelectedDate(event.target.value === "all" ? null : event.target.value)}
        className="w-full cursor-pointer appearance-none bg-transparent pr-4 text-[11px] font-medium tracking-[0.08em] uppercase outline-none"
      >
        <option value="all" className="bg-bg text-fg">All dates</option>
        {availableDates.map((date) => (
          <option key={date} value={date} className="bg-bg text-fg">
            {formatDateKey(date)}
          </option>
        ))}
      </select>
      <span aria-hidden className="pointer-events-none absolute right-3 text-[9px]">⌄</span>
    </label>
  );
}
