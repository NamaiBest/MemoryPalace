import { cn } from "@/lib/cn";
import { eventLabel, isUncategorized } from "@/lib/labels";
import type { EventType } from "@/types/moment";

const TONE: Record<EventType, string> = {
  capture: "text-accent",
  surprise: "text-surprise",
  excitement: "text-surprise",
  insight: "text-insight",
  error: "text-error",
  load: "text-load",
};

export function EventIcon({
  type,
  className,
}: {
  type: EventType;
  className?: string;
}) {
  const common = cn("h-3.5 w-3.5", TONE[type], className);
  if (type === "capture") {
    return (
      <svg viewBox="0 0 16 16" className={common} aria-hidden>
        <rect x="2" y="3.5" width="12" height="9" rx="2" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="8" cy="8" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    );
  }
  if (type === "surprise" || type === "excitement") {
    return (
      <svg viewBox="0 0 16 16" className={common} aria-hidden>
        <path
          d="M8 1.5 8.9 6.1 13.5 7 8.9 7.9 8 12.5 7.1 7.9 1.5 7 7.1 6.1Z"
          fill="currentColor"
        />
      </svg>
    );
  }
  if (type === "insight") {
    return (
      <svg viewBox="0 0 16 16" className={common} aria-hidden>
        <circle cx="8" cy="7" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path d="M8 10.4v2.4M6.4 13.2h3.2" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    );
  }
  if (type === "load") {
    return (
      <svg viewBox="0 0 16 16" className={common} aria-hidden>
        <path
          d="M1.5 11.2h2.1l1.6-3.4 1.7 5.2 1.8-8 1.7 6.2h4.2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 16 16" className={common} aria-hidden>
      <path
        d="M4.2 4.2 11.8 11.8M11.8 4.2 4.2 11.8"
        stroke="currentColor"
        strokeWidth="1.4"
      />
    </svg>
  );
}

export function EventLabel({
  type,
  confidence,
  className,
}: {
  type: EventType;
  /** Ranking score. Below the category threshold the label stays neutral. */
  confidence?: number;
  className?: string;
}) {
  const neutral = isUncategorized(type, confidence);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2",
        neutral ? "text-fg-mute" : TONE[type],
        className,
      )}
      title={neutral
        ? "The spike was too weak to assign a category, so none is claimed."
        : undefined}
    >
      {neutral ? (
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden>
          <circle cx="8" cy="8" r="5" fill="none" stroke="currentColor"
            strokeWidth="1.3" strokeDasharray="2.4 2.2" />
        </svg>
      ) : (
        <EventIcon type={type} />
      )}
      <span>{eventLabel(type, confidence)}</span>
    </span>
  );
}
