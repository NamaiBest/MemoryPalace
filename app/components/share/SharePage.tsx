"use client";

import { useState } from "react";
import { EmailDigest } from "@/components/share/EmailDigest";
import { IntensityDot } from "@/components/ui/IntensityDot";
import { useMoments } from "@/context/MomentsProvider";
import { cn } from "@/lib/cn";
import { formatDateKey, formatTime } from "@/lib/format";
import { momentTitle } from "@/lib/labels";

const MAX_SHARED = 12;

type Composed = {
  note: string;
  providerLabel: string;
  model: string;
  recipient: string;
  moments: { id: string; title?: string }[];
};

/**
 * Sharing a day with someone who was not in it.
 *
 * The wearer picks the moments by hand and nothing is sent anywhere until they press
 * share, because the whole point is that this is the one part of MemoryPalace another
 * person ever sees. Meta Muse Spark writes the note from the chosen moments only; the
 * text stays editable afterwards, since the last word about what gets said to someone
 * you love should be yours and not a model's.
 */
export function SharePage() {
  const { visibleMoments, selectedDate } = useMoments();
  const [picked, setPicked] = useState<string[]>([]);
  const [recipient, setRecipient] = useState("");
  const [composed, setComposed] = useState<Composed | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const toggle = (id: string) =>
    setPicked((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : current.length >= MAX_SHARED
          ? current
          : [...current, id],
    );

  const compose = async () => {
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const response = await fetch("/api/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ momentIds: picked, recipient }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "The note could not be written");
      setComposed(result);
      setDraft(result.note);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The note could not be written");
    } finally {
      setBusy(false);
    }
  };

  const share = async () => {
    const text = draft.trim();
    if (!text) return;
    // The Web Share sheet is the real thing on a phone. Everywhere else, the clipboard
    // is the honest fallback rather than pretending a message was delivered.
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title: "A few moments from my day", text });
        return;
      } catch {
        // Cancelled or unavailable; fall through to copying.
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setError("Copying was blocked. Select the text and copy it manually.");
    }
  };

  return (
    <main className="mx-auto w-full max-w-[1500px] px-6 pb-24 pt-32 md:px-12">
      {/* The heading left a wide empty column on desktop. Mailing yourself the day is
          the same instinct as sharing it with someone, one hour later, so it belongs
          beside the title rather than buried in settings. */}
      <div className="flex flex-col gap-10 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent">
            MemoryPalace / Share
          </p>
          <h1 className="mt-5 max-w-3xl text-balance font-serif text-5xl leading-[1.12] md:text-6xl">
            Send someone your day.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-fg-dim">
            Pick the moments that mattered
            {selectedDate ? ` on ${formatDateKey(selectedDate)}` : " today"}, and Meta Muse
            Spark writes them into something a person who was not there can actually feel.
            You get the last word before anything is sent.
          </p>
        </div>
        <EmailDigest date={selectedDate} selectedIds={picked} />
      </div>

      {visibleMoments.length === 0 ? (
        <p className="mt-12 text-fg-mute">
          There are no moments here yet. Capture a few and they will appear for sharing.
        </p>
      ) : (
        <>
          <div className="mt-12 flex flex-wrap items-center justify-between gap-4">
            <h2 className="font-serif text-2xl">Choose your key moments</h2>
            <span className="font-mono text-xs text-fg-mute">
              {picked.length} of {MAX_SHARED} selected
            </span>
          </div>

          <ul className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {visibleMoments.map((moment) => {
              const order = picked.indexOf(moment.id);
              const isPicked = order >= 0;
              return (
                <li key={moment.id}>
                  <button
                    type="button"
                    onClick={() => toggle(moment.id)}
                    aria-pressed={isPicked}
                    className={cn(
                      "group relative aspect-video w-full overflow-hidden rounded-xl border text-left transition-all",
                      isPicked
                        ? "border-accent ring-2 ring-accent/60 brightness-100"
                        : "border-white/10 brightness-[0.85] hover:brightness-100",
                    )}
                  >
                    {moment.media.thumbnailUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={moment.media.thumbnailUrl}
                        alt=""
                        className="absolute inset-0 h-full w-full object-cover"
                      />
                    ) : null}
                    <span className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-transparent" />
                    <IntensityDot
                      value={moment.confidence}
                      className="absolute left-3 top-3"
                    />
                    <span
                      className={cn(
                        "absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-full border font-mono text-[11px] backdrop-blur-md",
                        isPicked
                          ? "border-accent bg-accent text-bg"
                          : "border-white/25 bg-black/30 text-fg-dim",
                      )}
                    >
                      {isPicked ? order + 1 : "+"}
                    </span>
                    <span className="absolute inset-x-0 bottom-0 p-4">
                      <span className="block truncate text-sm text-fg">
                        {momentTitle(moment)}
                      </span>
                      <span className="mt-1 block font-mono text-[11px] text-fg/70">
                        {formatTime(moment.timestamp)}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <section className="mt-14 rounded-2xl border border-line bg-bg-raised/70 px-6 py-7 md:px-8">
            <div className="flex flex-wrap items-end gap-5">
              <label className="flex-1 min-w-[240px]">
                <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-fg-mute">
                  Who is this for
                </span>
                <input
                  value={recipient}
                  onChange={(event) => setRecipient(event.target.value)}
                  maxLength={80}
                  placeholder="Mum, my sister, Sam…"
                  className="mt-2 w-full rounded-xl border border-line-strong bg-bg/60 px-4 py-3 text-sm text-fg outline-none placeholder:text-fg-mute focus:border-accent"
                />
              </label>
              <button
                type="button"
                onClick={compose}
                disabled={busy || picked.length === 0}
                className="inline-flex items-center gap-3 rounded-xl bg-accent px-6 py-3.5 text-sm font-medium text-bg transition-colors hover:bg-fg disabled:cursor-default disabled:opacity-35"
              >
                {busy ? (
                  <>
                    <span className="processing-ring h-4 w-4" aria-hidden />
                    Muse Spark is writing…
                  </>
                ) : (
                  <>Write the note with Meta Muse Spark</>
                )}
              </button>
            </div>

            {error ? (
              <p role="alert" className="mt-5 text-sm text-[color:var(--color-error,#c48474)]">
                {error}
              </p>
            ) : null}

            {composed ? (
              <div className="mt-8">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-mono text-[10px] tracking-[0.18em] uppercase text-accent">
                    Written by {composed.providerLabel} · {composed.model}
                  </p>
                  <p className="font-mono text-[10px] text-fg-mute">
                    Grounded in {composed.moments.length} chosen moment
                    {composed.moments.length === 1 ? "" : "s"}
                  </p>
                </div>
                <textarea
                  value={draft}
                  onChange={(event) => {
                    setDraft(event.target.value);
                    setCopied(false);
                  }}
                  rows={8}
                  aria-label="Your message, editable before sending"
                  className="mt-3 w-full resize-y rounded-xl border border-line-strong bg-bg/60 px-5 py-4 text-[15px] leading-7 text-fg outline-none focus:border-accent"
                />
                <div className="mt-4 flex flex-wrap items-center gap-4">
                  <button
                    type="button"
                    onClick={share}
                    className="inline-flex rounded-xl bg-accent px-6 py-3 text-sm font-medium text-bg transition-colors hover:bg-fg"
                  >
                    Share with {composed.recipient || "someone you love"}
                  </button>
                  {copied ? (
                    <span role="status" className="font-mono text-xs text-ok">
                      Copied. Paste it wherever you talk to them.
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}
          </section>
        </>
      )}
    </main>
  );
}
