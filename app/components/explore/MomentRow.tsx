"use client";

import { useRouter } from "next/navigation";
import { EventIcon } from "@/components/ui/EventLabel";
import { formatConfidence, formatDateTime } from "@/lib/format";
import { eventLabel, formatModalities, STATUS_LABELS } from "@/lib/labels";
import type { Moment } from "@/types/moment";

export function MomentRow({ moment }: { moment: Moment }) {
  const router = useRouter();

  return (
    <tr
      tabIndex={0}
      onClick={() => router.push(`/moment/${moment.id}`)}
      onKeyDown={(event) => {
        if (event.key === "Enter") router.push(`/moment/${moment.id}`);
      }}
      className="cursor-pointer border-b border-line text-sm transition-colors hover:bg-fg/[0.035] focus-visible:bg-fg/[0.05] focus-visible:outline-none"
    >
      <td className="whitespace-nowrap py-3.5 pr-4">
        <span className="inline-flex items-center gap-2.5 font-mono text-[13px]">
          <EventIcon type={moment.eventType} />
          {moment.id}
        </span>
      </td>
      <td className="whitespace-nowrap py-3.5 pr-4 text-fg-dim">
        {formatDateTime(moment.timestamp)}
      </td>
      <td className="py-3.5 pr-4">{eventLabel(moment.eventType)}</td>
      <td className="whitespace-nowrap py-3.5 pr-4 font-mono text-fg-dim">
        {formatConfidence(moment.confidence)}
      </td>
      <td className="hidden py-3.5 pr-4 text-fg-dim md:table-cell">
        {formatModalities(moment)}
      </td>
      <td className="hidden whitespace-nowrap py-3.5 text-fg-mute lg:table-cell">
        {STATUS_LABELS[moment.status]}
      </td>
    </tr>
  );
}
