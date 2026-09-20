"use client";

import { useRouter } from "next/navigation";
import { useMoments } from "@/context/MomentsProvider";
import type { Moment } from "@/types/moment";

export function MomentActions({ moment }: { moment: Moment }) {
  const { keepMoment, deleteMoment } = useMoments();
  const router = useRouter();
  const kept = moment.status === "kept";

  return (
    <div className="flex flex-wrap gap-3">
      <button
        type="button"
        onClick={() => keepMoment(moment.id)}
        className="border border-ok/50 px-4 py-2 text-[11px] tracking-[0.18em] uppercase text-ok transition-colors hover:bg-ok hover:text-bg"
      >
        {kept ? "Moment kept" : "Keep moment"}
      </button>
      <button
        type="button"
        onClick={() => {
          deleteMoment(moment.id);
          router.push("/");
        }}
        className="border border-error/40 px-4 py-2 text-[11px] tracking-[0.18em] uppercase text-error transition-colors hover:bg-error hover:text-bg"
      >
        Delete moment
      </button>
    </div>
  );
}
