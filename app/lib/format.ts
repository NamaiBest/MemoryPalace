// Everything renders in Boston time regardless of where the viewer or the server is.
// Pinning the zone also removes a hydration hazard: without it the server formats in
// its own locale and the browser in another, and the two disagree on first paint.
export const TIME_ZONE = "America/New_York";
export const TIME_ZONE_LABEL = "Boston";

const TIME = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  timeZone: TIME_ZONE,
});

const TIME_WITH_SECONDS = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
  hour12: true,
  timeZone: TIME_ZONE,
});

const DATE_TIME = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  timeZone: TIME_ZONE,
});

const DATE = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: TIME_ZONE,
});

const FULL = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
  hour12: true,
  timeZone: TIME_ZONE,
});

export function formatTime(iso: string): string {
  return TIME.format(new Date(iso));
}

export function formatTimeWithSeconds(iso: string): string {
  return TIME_WITH_SECONDS.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return DATE_TIME.format(new Date(iso));
}

export function formatDate(iso: string): string {
  return DATE.format(new Date(iso));
}

/** Date + time to the second, in Boston. Used where exactness matters more than brevity. */
export function formatFull(iso: string): string {
  return `${FULL.format(new Date(iso))} ${TIME_ZONE_LABEL}`;
}

/** "just now" / "4m ago" / "2h ago" — for showing that something is live. */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const seconds = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 90) return `${Math.round(seconds)}s ago`;
  const minutes = seconds / 60;
  if (minutes < 90) return `${Math.round(minutes)}m ago`;
  const hours = minutes / 60;
  if (hours < 36) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatMomentNumber(sequence: number): string {
  return `Moment #${String(sequence).padStart(3, "0")}`;
}

export function formatContextWindow(start: string, end: string): string {
  return `${formatTimeWithSeconds(start)} → ${formatTimeWithSeconds(end)}`;
}

export function isSameDay(iso: string, comparedTo: Date = new Date()): boolean {
  const date = new Date(iso);
  return (
    date.getFullYear() === comparedTo.getFullYear() &&
    date.getMonth() === comparedTo.getMonth() &&
    date.getDate() === comparedTo.getDate()
  );
}

export function hoursAgo(iso: string, now: Date = new Date()): number {
  return (now.getTime() - new Date(iso).getTime()) / 3_600_000;
}
