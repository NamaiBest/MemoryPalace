import { hoursAgo, isSameDay } from "@/lib/format";
import { eventLabel, getModalities } from "@/lib/labels";
import type { EventType, Modality, Moment } from "@/types/moment";

export type EventFilter = "all" | EventType;
export type ConfidenceFilter = "all" | "high" | "medium" | "low";
export type ModalityFilter = "all" | Modality;
export type DateFilter = "all" | "today" | "recent";

export function matchesSearch(moment: Moment, query: string): boolean {
  const value = query.trim().toLowerCase();
  if (!value) return true;
  return [
    moment.id,
    String(moment.sequence),
    String(moment.sequence).padStart(3, "0"),
    eventLabel(moment.eventType),
    moment.eventType,
    moment.annotation,
    moment.summary,
  ]
    .join(" ")
    .toLowerCase()
    .includes(value);
}

export function matchesFilters(
  moment: Moment,
  filters: {
    event: EventFilter;
    confidence: ConfidenceFilter;
    modality: ModalityFilter;
    date: DateFilter;
    query: string;
  },
): boolean {
  if (!matchesSearch(moment, filters.query)) return false;
  if (filters.event !== "all" && moment.eventType !== filters.event) return false;

  const percent = moment.confidence * 100;
  if (filters.confidence === "high" && percent < 80) return false;
  if (filters.confidence === "medium" && (percent < 60 || percent >= 80)) {
    return false;
  }
  if (filters.confidence === "low" && percent >= 60) return false;

  if (
    filters.modality !== "all" &&
    !getModalities(moment).includes(filters.modality)
  ) {
    return false;
  }

  if (filters.date === "today" && !isSameDay(moment.timestamp)) return false;
  if (filters.date === "recent" && hoursAgo(moment.timestamp) > 48) return false;

  return true;
}
