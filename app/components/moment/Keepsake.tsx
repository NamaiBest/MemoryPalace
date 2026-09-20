"use client";

import { useState } from "react";
import type { Moment } from "@/types/moment";

/**
 * A keepsake illustration of one moment, drawn by Meta Muse Image.
 *
 * Deliberately illustrative rather than photoreal. A photoreal render of something the
 * camera never saw would be a fabricated memory sitting in the same gallery as real
 * footage, so the style is part of the feature working correctly, not decoration. The
 * label under the image says what made it, for the same reason.
 */
export function Keepsake({ moment }: { moment: Moment }) {
  const [url, setUrl] = useState<string | null>(moment.keepsakeUrl ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/moments/keepsake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ momentId: moment.id }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "Could not draw this moment");
      setUrl(result.keepsakeUrl);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not draw this moment");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-10 border-t border-line pt-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl text-fg">Keep this one</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-fg-dim">
            Turn this moment into something you would actually put on a wall. Drawn from
            what the camera saw, as an illustration rather than a photograph.
          </p>
        </div>
        <button
          type="button"
          onClick={generate}
          disabled={busy}
          className="inline-flex items-center gap-3 rounded-xl bg-accent px-6 py-3 text-sm font-medium text-bg transition-colors hover:bg-fg disabled:cursor-default disabled:opacity-40"
        >
          {busy ? (
            <>
              <span className="processing-ring h-4 w-4" aria-hidden />
              Drawing…
            </>
          ) : url ? (
            "Draw it again"
          ) : (
            "Generate keepsake"
          )}
        </button>
      </div>

      {error ? (
        <p role="alert" className="mt-5 text-sm text-error">{error}</p>
      ) : null}

      {url ? (
        <figure className="mt-7">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            key={url}
            src={url}
            alt={`An illustrated keepsake of ${moment.semanticTitle ?? "this moment"}`}
            className="w-full rounded-2xl border border-line"
          />
          <figcaption className="mt-3 font-mono text-[10px] tracking-[0.16em] uppercase text-fg-mute">
            Illustration by Meta Muse Image, from this moment&apos;s own description
          </figcaption>
        </figure>
      ) : null}
    </section>
  );
}
