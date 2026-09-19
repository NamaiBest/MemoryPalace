import { cn } from "@/lib/cn";
import { getModalities, MODALITY_LABELS } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function ModalityPills({
  moment,
  className,
}: {
  moment: Moment;
  className?: string;
}) {
  return (
    <ul className={cn("flex flex-wrap gap-2", className)}>
      {getModalities(moment).map((modality) => (
        <li
          key={modality}
          className="border border-line-strong px-2 py-0.5 text-[10px] tracking-[0.16em] uppercase text-fg-dim"
        >
          {MODALITY_LABELS[modality]}
        </li>
      ))}
    </ul>
  );
}
