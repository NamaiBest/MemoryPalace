import { hoursAgo, isSameDay } from "@/lib/format";
import { eventLabel, getModalities } from "@/lib/labels";
import type { EventType, Modality, Moment } from "@/types/moment";

export type EventFilter = "all" | EventType;
export type ConfidenceFilter = "all" | "critical" | "high" | "moderate" | "weak";
export type ModalityFilter = "all" | Modality;
export type DateFilter = "all" | "today" | "recent";

export function matchesSearch(moment: Moment, query: string): boolean {
  const value = query.trim().toLowerCase();
  if (!value) return true;
  return [
    moment.id,
    moment.semanticTitle ?? "",
    String(moment.sequence),
    String(moment.sequence).padStart(3, "0"),
    eventLabel(moment.eventType),
    moment.eventType,
    moment.annotation,
    moment.summary,
    moment.aiDescription ?? "",
    moment.transcript ?? "",
    ...(moment.keywords ?? []),
    ...(moment.topics ?? []),
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
    session?: string;
    query: string;
  },
): boolean {
  if (!matchesSearch(moment, filters.query)) return false;
  if (filters.event !== "all" && moment.eventType !== filters.event) return false;

  const intensity = moment.confidence;
  if (filters.confidence === "critical" && intensity < 0.85) return false;
  if (filters.confidence === "high" && (intensity < 0.7 || intensity >= 0.85)) {
    return false;
  }
  if (filters.confidence === "moderate" && (intensity < 0.55 || intensity >= 0.7)) {
    return false;
  }
  if (filters.confidence === "weak" && intensity >= 0.55) return false;

  if (
    filters.modality !== "all" &&
    !getModalities(moment).includes(filters.modality)
  ) {
    return false;
  }

  if (filters.date === "today" && !isSameDay(moment.timestamp)) return false;
  if (filters.date === "recent" && hoursAgo(moment.timestamp) > 48) return false;
  if (filters.session && filters.session !== "all" && moment.sessionId !== filters.session) {
    return false;
  }

  return true;
}
