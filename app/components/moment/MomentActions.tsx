"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMoments } from "@/context/MomentsProvider";
import type { Moment } from "@/types/moment";

export function MomentActions({ moment }: { moment: Moment }) {
  const { keepMoment, deleteMoment } = useMoments();
  const router = useRouter();
  const kept = moment.status === "kept";
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={() => keepMoment(moment.id)}
        className="border border-ok/50 px-4 py-2 text-[11px] tracking-[0.18em] uppercase text-ok transition-colors hover:bg-ok hover:text-bg"
      >
        {kept ? "Moment kept" : "Keep moment"}
      </button>
      <button
        type="button"
        disabled={deleting}
        onClick={async () => {
          setDeleting(true);
          setDeleteError(null);
          try {
            await deleteMoment(moment.id);
            router.push("/");
          } catch (error) {
            setDeleteError(error instanceof Error ? error.message : "Delete failed");
            setDeleting(false);
          }
        }}
        className="border border-error/40 px-4 py-2 text-[11px] tracking-[0.18em] uppercase text-error transition-colors hover:bg-error hover:text-bg disabled:cursor-wait disabled:opacity-60"
      >
        {deleting ? "Deleting…" : "Delete moment"}
      </button>
      {deleteError && <p role="alert" className="w-full text-xs text-error">{deleteError}</p>}
    </div>
  );
}
