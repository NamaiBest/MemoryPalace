"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { AnnotationEditor } from "@/components/moment/AnnotationEditor";
import { EEGChart } from "@/components/moment/EEGChart";
import { MomentActions } from "@/components/moment/MomentActions";
import { MomentMedia } from "@/components/moment/MomentMedia";
import { MomentMetadata } from "@/components/moment/MomentMetadata";
import { useMoments } from "@/context/MomentsProvider";

export function MomentDetailPage() {
  const params = useParams<{ id: string }>();
  const { getMoment } = useMoments();
  const moment = getMoment(params.id);

  if (!moment || moment.status === "deleted") {
    return (
      <main className="mx-auto max-w-3xl px-5 pb-20 pt-28 md:px-8">
        <p className="font-serif text-3xl">Moment unavailable</p>
        <p className="mt-3 text-sm text-fg-dim">
          This candidate is no longer in the repository.
        </p>
        <Link
          href="/explore"
          className="mt-8 inline-flex text-[11px] tracking-[0.18em] uppercase text-accent"
        >
          Back to Explore
        </Link>
      </main>
    );
  }

  return (
    <main className="pb-24 pt-16">
      <MomentMedia moment={moment} />
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="flex flex-wrap items-center justify-between gap-4 py-5">
          <Link
            href="/"
            className="text-[11px] tracking-[0.16em] uppercase text-fg-dim hover:text-fg"
          >
            ← Home
          </Link>
          <MomentActions moment={moment} />
        </div>
        <MomentMetadata moment={moment} />
        <div className="mt-8 grid gap-6">
          {moment.eeg ? <EEGChart eeg={moment.eeg} /> : null}
          <AnnotationEditor key={moment.id} moment={moment} />
        </div>
      </div>
    </main>
  );
}
