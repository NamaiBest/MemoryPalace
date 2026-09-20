"use client";

import { useState } from "react";

/**
 * Mail the day to an inbox, written by Meta Muse Spark.
 *
 * Sharing to a person and mailing yourself are the same instinct at different hours:
 * one is "you should see this", the other is "I should not have missed this". They sit
 * on the same page because they are the same act, so this fills the space beside the
 * heading rather than hiding on a settings screen.
 */
export function EmailDigest({ date }: { date: string | null }) {
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const address = to.trim();
    if (!address) {
      setError("Who should it go to?");
      return;
    }
    setBusy(true);
    setError(null);
    setSent(null);
    try {
      const response = await fetch("/api/digest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: address, date, send: true }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "The email could not be sent");
      setSent(result.subject ?? "Your day");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The email could not be sent");
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="w-full max-w-sm rounded-2xl border border-line bg-bg-raised/60 px-6 py-6">
      <p className="font-mono text-[10px] tracking-[0.18em] uppercase text-accent">
        Or mail it to yourself
      </p>
      <h2 className="mt-3 font-serif text-2xl leading-snug">
        The whole day, in your inbox
      </h2>
      <p className="mt-3 text-sm leading-6 text-fg-dim">
        Memory Guard reads every moment{date ? " from that day" : " from today"} and
        writes it as one story. It arrives on its own each evening if you never came
        back to look.
      </p>

      <label className="mt-5 block">
        <span className="sr-only">Email address</span>
        <input
          type="email"
          inputMode="email"
          autoComplete="email"
          value={to}
          onChange={(event) => {
            setTo(event.target.value);
            setError(null);
            setSent(null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !busy) void send();
          }}
          placeholder="you@example.com"
          className="w-full rounded-xl border border-line-strong bg-bg/60 px-4 py-3 text-sm text-fg outline-none placeholder:text-fg-mute focus:border-accent"
        />
      </label>

      <button
        type="button"
        onClick={send}
        disabled={busy}
        className="mt-3 inline-flex w-full items-center justify-center gap-3 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-bg transition-colors hover:bg-fg disabled:cursor-default disabled:opacity-40"
      >
        {busy ? (
          <>
            <span className="processing-ring h-4 w-4" aria-hidden />
            Writing and sending…
          </>
        ) : (
          "Send me the day"
        )}
      </button>

      {sent ? (
        <p role="status" className="mt-4 text-sm leading-6 text-ok">
          Sent. Look for “{sent}”.
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
