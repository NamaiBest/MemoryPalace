"use client";

import { useState } from "react";

/**
 * Mail a stretch of days to an inbox, written by Meta Muse Spark.
 *
 * Two intents share this card because they are one act pointed in two directions:
 * "I should not have missed this" and "you should see this". Sending to yourself needs
 * no typing, since the address is already configured; sending to someone else opens the
 * range controls, because what you send a person is rarely exactly one day.
 */

const RANGES = [
  { days: 1, label: "Today" },
  { days: 2, label: "Last 2 days" },
  { days: 3, label: "Last 3 days" },
  { days: 7, label: "Last week" },
] as const;

export function EmailDigest({
  date,
  selectedIds = [],
}: {
  date: string | null;
  /** Moments hand-picked above. When present they beat the range entirely. */
  selectedIds?: string[];
}) {
  const [mode, setMode] = useState<"me" | "other">("me");
  const [to, setTo] = useState("");
  const [days, setDays] = useState<number>(1);
  const [useSelection, setUseSelection] = useState(false);
  const [attach, setAttach] = useState(true);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const picking = useSelection && selectedIds.length > 0;

  async function send() {
    if (mode === "other" && !to.trim()) {
      setError("Who should it go to?");
      return;
    }
    setBusy(true);
    setError(null);
    setSent(null);
    setNote(null);
    try {
      const response = await fetch("/api/digest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          // Omitting `to` falls back to the configured address, so sending to
          // yourself never requires typing it.
          to: mode === "other" ? to.trim() : undefined,
          date,
          days: picking ? 1 : days,
          momentIds: picking ? selectedIds : undefined,
          attach,
          send: true,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "The email could not be sent");
      setSent(result.subject ?? "Your day");
      if (result.attachedFiles) {
        setNote(
          `${result.attachedFiles} file${result.attachedFiles === 1 ? "" : "s"} attached` +
            (result.clipsSkipped
              ? `, ${result.clipsSkipped} clip${result.clipsSkipped === 1 ? "" : "s"} left out to stay deliverable`
              : ""),
        );
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The email could not be sent");
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="w-full max-w-sm rounded-2xl border border-line bg-bg-raised/60 px-6 py-6">
      <p className="font-mono text-[10px] tracking-[0.18em] uppercase text-accent">
        Or mail it
      </p>
      <h2 className="mt-3 font-serif text-2xl leading-snug">
        The whole day, in an inbox
      </h2>

      <div className="mt-5 flex rounded-xl border border-line-strong p-1">
        {(["me", "other"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => { setMode(option); setSent(null); setError(null); }}
            aria-pressed={mode === option}
            className={`flex-1 rounded-lg px-3 py-2 text-xs transition-colors ${
              mode === option ? "bg-accent text-bg" : "text-fg-dim hover:text-fg"
            }`}
          >
            {option === "me" ? "Send to me" : "Someone else"}
          </button>
        ))}
      </div>

      {mode === "other" ? (
        <label className="mt-3 block">
          <span className="sr-only">Their email address</span>
          <input
            type="email"
            inputMode="email"
            autoComplete="email"
            value={to}
            onChange={(event) => { setTo(event.target.value); setError(null); }}
            onKeyDown={(event) => { if (event.key === "Enter" && !busy) void send(); }}
            placeholder="them@example.com"
            className="w-full rounded-xl border border-line-strong bg-bg/60 px-4 py-3 text-sm text-fg outline-none placeholder:text-fg-mute focus:border-accent"
          />
        </label>
      ) : null}

      <fieldset className="mt-4" disabled={picking}>
        <legend className="font-mono text-[10px] tracking-[0.16em] uppercase text-fg-mute">
          How much
        </legend>
        <div className={`mt-2 grid grid-cols-2 gap-2 ${picking ? "opacity-35" : ""}`}>
          {RANGES.map((range) => (
            <button
              key={range.days}
              type="button"
              onClick={() => setDays(range.days)}
              aria-pressed={!picking && days === range.days}
              className={`rounded-lg border px-3 py-2 text-xs transition-colors ${
                !picking && days === range.days
                  ? "border-accent bg-accent/10 text-fg"
                  : "border-line-strong text-fg-dim hover:text-fg"
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </fieldset>

      {selectedIds.length > 0 ? (
        <label className="mt-3 flex cursor-pointer items-center gap-3 text-xs text-fg-dim">
          <input
            type="checkbox"
            checked={useSelection}
            onChange={(event) => setUseSelection(event.target.checked)}
            className="h-4 w-4 accent-[var(--color-accent)]"
          />
          Just the {selectedIds.length} moment{selectedIds.length === 1 ? "" : "s"} I picked above
        </label>
      ) : null}

      <label className="mt-3 flex cursor-pointer items-center gap-3 text-xs text-fg-dim">
        <input
          type="checkbox"
          checked={attach}
          onChange={(event) => setAttach(event.target.checked)}
          className="h-4 w-4 accent-[var(--color-accent)]"
        />
        Attach the stills, and the clips that fit
      </label>

      <button
        type="button"
        onClick={send}
        disabled={busy}
        className="mt-4 inline-flex w-full items-center justify-center gap-3 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-bg transition-colors hover:bg-fg disabled:cursor-default disabled:opacity-40"
      >
        {busy ? (
          <>
            <span className="processing-ring h-4 w-4" aria-hidden />
            Writing and sending…
          </>
        ) : mode === "me" ? (
          "Send recap now"
        ) : (
          "Send it to them"
        )}
      </button>

      {sent ? (
        <p role="status" className="mt-4 text-sm leading-6 text-ok">
          Sent. Look for “{sent}”.
          {note ? <span className="mt-1 block text-fg-mute">{note}</span> : null}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 text-sm leading-6 text-error">{error}</p>
      ) : null}

      <p className="mt-5 border-t border-line pt-4 font-mono text-[10px] tracking-[0.14em] uppercase text-fg-mute">
        Written by Meta Muse Spark
      </p>
    </aside>
  );
}
