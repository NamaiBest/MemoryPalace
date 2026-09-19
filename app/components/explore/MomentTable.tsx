import { MomentRow } from "@/components/explore/MomentRow";
import type { Moment } from "@/types/moment";

export function MomentTable({ moments }: { moments: Moment[] }) {
  if (moments.length === 0) {
    return (
      <div className="border border-dashed border-line-strong px-6 py-16 text-center">
        <p className="text-sm text-fg-dim">No moments match these filters.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line text-[10px] tracking-[0.16em] uppercase text-fg-mute">
            <th className="py-3 pr-4 font-medium">Moment</th>
            <th className="py-3 pr-4 font-medium">Timestamp</th>
            <th className="py-3 pr-4 font-medium">Event type</th>
            <th className="py-3 pr-4 font-medium">Confidence</th>
            <th className="hidden py-3 pr-4 font-medium md:table-cell">
              Modalities
            </th>
            <th className="hidden py-3 font-medium lg:table-cell">Status</th>
          </tr>
        </thead>
        <tbody>
          {moments.map((moment) => (
            <MomentRow key={moment.id} moment={moment} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
