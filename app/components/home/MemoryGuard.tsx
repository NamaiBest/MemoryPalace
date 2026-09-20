"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMoments } from "@/context/MomentsProvider";
import { formatDateKey } from "@/lib/format";

type GuardStatus = {
  agent?: {
    name: string;
    provider: "meta" | "grok";
    providerLabel: string;
    model: string;
    configured: boolean;
    fallbackAvailable?: boolean;
    error?: string | null;
  };
  elastic?: { configured: boolean; ready: boolean };
  offline?: boolean;
};

type GuardAnswer = {
  answer: string;
  providerLabel: string;
  model: string;
  retrievalEngine: string;
  error?: string;
};

const SUGGESTIONS = [
  "What were my strongest moments?",
  "What was being discussed?",
  "Find something worth revisiting.",
];

export function MemoryGuard() {
  const { selectedDate } = useMoments();
  const [open, setOpen] = useState(true);
  const [status, setStatus] = useState<GuardStatus>({});
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<GuardAnswer | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/agent", { cache: "no-store" })
      .then(async (response) => ({ ...(await response.json()), offline: !response.ok }))
      .then(setStatus)
      .catch(() => setStatus({ offline: true }));
  }, []);

  async function ask(event: FormEvent) {
    event.preventDefault();
    const prompt = question.trim();
    if (!prompt || busy) return;
    setBusy(true);
    setResult(null);
    try {
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt, date: selectedDate }),
      });
      const body = (await response.json()) as GuardAnswer;
      if (!response.ok) throw new Error(body.error || "Memory Guard could not answer");
      setResult(body);
    } catch (error) {
      setResult({
        answer: error instanceof Error ? error.message : "Memory Guard could not answer",
        providerLabel: status.agent?.providerLabel ?? "Selected model",
        model: status.agent?.model ?? "offline",
        retrievalEngine: "unavailable",
      });
    } finally {
      setBusy(false);
    }
  }

  const usingModel = Boolean(status.agent?.configured && !status.agent?.error);
  const provider = usingModel
    ? status.agent?.providerLabel ?? "Selected model"
    : "Local Memory Guard";
  const providerReady = Boolean(!status.offline && (usingModel || status.agent?.fallbackAvailable));

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-3 rounded-full border border-white/15 bg-bg/80 px-5 py-3 text-sm text-fg shadow-2xl backdrop-blur-2xl transition hover:border-accent/50"
        aria-label="Open Memory Guard"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_18px_var(--accent)]" />
        Memory Guard
      </button>
    );
  }

  return (
    <aside className="fixed bottom-5 right-5 z-40 w-[calc(100%-2.5rem)] max-w-[410px] overflow-hidden rounded-[28px] border border-white/15 bg-[#111113]/88 shadow-[0_24px_90px_rgba(0,0,0,.55)] backdrop-blur-2xl lg:bottom-auto lg:top-24">
      <div className="border-b border-white/10 px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl border border-accent/30 bg-accent/10">
              <span className="h-3 w-3 rounded-full bg-accent shadow-[0_0_20px_var(--accent)]" />
            </div>
            <div>
              <p className="text-sm font-medium text-fg">Memory Guard</p>
              <p className="text-[11px] tracking-[0.12em] text-fg-mute uppercase">
                {provider} · {usingModel ? status.agent?.model : "grounded catalog"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-full px-2 py-1 text-lg leading-none text-fg-mute transition hover:bg-white/5 hover:text-fg"
            aria-label="Minimize Memory Guard"
          >
            −
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-[10px] tracking-[0.12em] uppercase">
          <span className={`rounded-full border px-2.5 py-1 ${providerReady ? "border-ok/30 bg-ok/10 text-ok" : "border-white/10 text-fg-mute"}`}>
            {providerReady ? (usingModel ? "Agent ready" : "Grounded local") : "Agent offline"}
          </span>
          <span className="rounded-full border border-white/10 px-2.5 py-1 text-fg-dim">
            {status.elastic?.configured ? "Elastic retrieval" : "Local retrieval"}
          </span>
        </div>
      </div>

      <div className="space-y-4 px-5 py-5">
        <p className="text-sm leading-6 text-fg-dim">
          Ask across {selectedDate ? `moments from ${formatDateKey(selectedDate)}` : "all captured moments"}, visual context, and spike intensity.
        </p>
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setQuestion(suggestion)}
              className="rounded-full border border-white/10 bg-white/[.035] px-3 py-1.5 text-left text-[11px] text-fg-dim transition hover:border-accent/30 hover:text-fg"
            >
              {suggestion}
            </button>
          ))}
        </div>
        {result && (
          <div className="max-h-40 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm leading-6 text-fg/85">{result.answer}</p>
            <p className="mt-3 text-[10px] tracking-[0.12em] text-fg-mute uppercase">
              {result.providerLabel} · {result.retrievalEngine}
            </p>
          </div>
        )}
        <form onSubmit={ask} className="flex gap-2">
          <label className="sr-only" htmlFor="memory-guard-question">Ask Memory Guard</label>
          <input
            id="memory-guard-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={2000}
            placeholder="Ask about a memory…"
            className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-white/[.045] px-4 py-3 text-sm text-fg placeholder:text-fg-mute focus:border-accent/50 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!question.trim() || busy}
            className="rounded-2xl bg-fg px-4 py-3 text-sm font-medium text-bg transition hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "…" : "Ask"}
          </button>
        </form>
      </div>
    </aside>
  );
}
