import { cn } from "@/lib/cn";
import { formatConfidence } from "@/lib/format";
import { intensityMeta } from "@/lib/intensity";

export function IntensityDot({
  value,
  showLabel = false,
  className,
}: {
  value: number;
  showLabel?: boolean;
  className?: string;
}) {
  const intensity = intensityMeta(value);
  const title = `${intensity.label} spike intensity · ${formatConfidence(value)}`;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/55 px-2.5 py-1.5 text-[10px] font-medium tracking-[0.12em] uppercase text-white backdrop-blur-md",
        className,
      )}
      title={title}
      aria-label={title}
    >
      <span
        aria-hidden
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{
          backgroundColor: intensity.color,
          boxShadow: `0 0 12px ${intensity.color}`,
        }}
      />
      {showLabel ? intensity.label : null}
    </span>
  );
}

