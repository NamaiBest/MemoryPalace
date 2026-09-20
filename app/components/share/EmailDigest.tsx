"use client";

import { useEffect, useState } from "react";

/**
 * Mail a stretch of days, or the moments you picked, written by Meta Muse Spark.
 *
 * Kept deliberately short. It sits beside the page heading, and anything taller pushes
 * the moment grid down the page and leaves a dead band of empty space next to the text.
 * So the controls are one row each rather than stacked cards.
 *
 * Clips are opt in and only ever the ones picked by hand. A day of video is roughly
 * 80 MB and a mailbox rejects anything past 25 MB, so "everything" was never on offer.
 */

const RANGES = [
  { days: 1, label: "1d" },
  { days: 2, label: "2d" },
  { days: 3, label: "3d" },
  { days: 7, label: "1w" },
] as const;

export function EmailDigest({
  date,
  selectedIds = [],
}: {
  date: string | null;
  selectedIds?: string[];
}) {
  const [contact, setContact] = useState<string>("me");
  const [saved, setSaved] = useState<{ label: string; address: string }[]>([]);
  const [custom, setCustom] = useState("");
  const [days, setDays] = useState(1);
  const [withClips, setWithClips] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Favourites are configured on the backend, so no address is baked into this file.
  useEffect(() => {
    let live = true;
    fetch("/api/digest")
      .then((response) => response.json())
      .then((body) => { if (live) setSaved(body.contacts ?? []); })
      .catch(() => undefined);
    return () => { live = false; };
  }, []);

  const hasSelection = selectedIds.length > 0;
  const picking = withClips && hasSelection;
  const preset = saved.find((c) => c.label === contact);

  async function send() {
    const address = contact === "custom" ? custom.trim() : preset?.address;
    if (contact === "custom" && !address) {
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
          // No address means the configured one, so sending to yourself needs no typing.
          to: address,
          date,
          days: picking ? 1 : days,
          momentIds: picking ? selectedIds : undefined,
          attach: picking,
          send: true,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "The email could not be sent");
      setSent(result.subject ?? "Your day");
      if (result.attachedFiles) {
        setNote(
          `${result.attachedFiles} clip${result.attachedFiles === 1 ? "" : "s"} attached` +
            (result.clipsSkipped ? `, ${result.clipsSkipped} too large to send` : ""),
        );
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The email could not be sent");
    } finally {
      setBusy(false);
    }
  }

  const chip = (active: boolean) =>
    `rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:cursor-default disabled:opacity-35 ${
      active ? "border-accent bg-accent/10 text-fg"
             : "border-line-strong text-fg-dim hover:enabled:text-fg"
    }`;

  return (
    <aside className="w-full max-w-sm rounded-2xl border border-line bg-bg-raised/60 px-5 py-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-serif text-xl leading-snug">Mail it instead</h2>
        <span className="font-mono text-[9px] tracking-[0.14em] uppercase text-fg-mute">
          Muse Spark
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={() => setContact("me")}
          aria-pressed={contact === "me"} className={chip(contact === "me")}>
          Me
        </button>
        {saved.map((option) => (
          <button key={option.label} type="button" onClick={() => setContact(option.label)}
            aria-pressed={contact === option.label} className={chip(contact === option.label)}>
            {option.label}
          </button>
        ))}
        <button type="button" onClick={() => setContact("custom")}
          aria-pressed={contact === "custom"} className={chip(contact === "custom")}>
          Someone else
        </button>
      </div>

      {contact === "custom" ? (
        <input
          type="email" inputMode="email" autoComplete="email" value={custom}
          onChange={(event) => { setCustom(event.target.value); setError(null); }}
          onKeyDown={(event) => { if (event.key === "Enter" && !busy) void send(); }}
          placeholder="them@example.com"
          className="mt-2 w-full rounded-lg border border-line-strong bg-bg/60 px-3 py-2 text-xs text-fg outline-none placeholder:text-fg-mute focus:border-accent"
        />
      ) : null}

      <div className="mt-4 flex items-center gap-2">
        <span className="font-mono text-[9px] tracking-[0.14em] uppercase text-fg-mute">
          How much
        </span>
        <div className={`flex gap-1.5 ${picking ? "opacity-35" : ""}`}>
          {RANGES.map((range) => (
            <button key={range.days} type="button" disabled={picking}
              onClick={() => setDays(range.days)}
              aria-pressed={!picking && days === range.days}
              className={chip(!picking && days === range.days)}>
              {range.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex gap-2">
        <button type="button" onClick={() => setWithClips(false)}
          aria-pressed={!withClips} className={`flex-1 ${chip(!withClips)}`}>
          Summary only
        </button>
        <button type="button" onClick={() => hasSelection && setWithClips(true)}
          aria-pressed={withClips} disabled={!hasSelection}
          title={hasSelection ? undefined : "Pick moments below to send their clips"}
          className={`flex-1 ${chip(withClips)}`}>
          + {hasSelection ? selectedIds.length : ""} clip{selectedIds.length === 1 ? "" : "s"}
        </button>
      </div>

      <button type="button" onClick={send} disabled={busy}
        className="mt-4 inline-flex w-full items-center justify-center gap-3 rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-bg transition-colors hover:bg-fg disabled:cursor-default disabled:opacity-40">
        {busy ? (
          <><span className="processing-ring h-4 w-4" aria-hidden />Writing and sending…</>
        ) : (
          `Send recap${contact !== "me" && contact !== "custom" ? ` to ${contact}` : ""}`
        )}
      </button>

      {sent ? (
        <p role="status" className="mt-3 text-xs leading-5 text-ok">
          Sent. Look for “{sent}”.
          {note ? <span className="mt-0.5 block text-fg-mute">{note}</span> : null}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-3 text-xs leading-5 text-error">{error}</p>
      ) : null}
    </aside>
  );
}
