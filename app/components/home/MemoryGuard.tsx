"use client";

import Link from "next/link";
import { FormEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useMoments } from "@/context/MomentsProvider";
import { cn } from "@/lib/cn";
import { formatDateKey } from "@/lib/format";
import { momentTitle } from "@/lib/labels";
import type { Moment } from "@/types/moment";

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
  voice?: {
    provider: "meta";
    model: string;
    configured: boolean;
    mode: string;
    output: string;
    error?: string | null;
  };
  offline?: boolean;
};

type GuardAnswer = {
  answer: string;
  providerLabel: string;
  model: string;
  retrievalEngine: string;
  momentIds?: string[];
  transcript?: string;
  voice?: {
    inputProvider: string;
    inputModel: string;
    outputProvider: string;
  };
  error?: string;
};

type ConversationTurn = { role: "user" | "assistant"; content: string };
type VoiceState = "idle" | "listening" | "thinking" | "speaking" | "error";

const SUGGESTIONS = [
  "What were my strongest moments?",
  "What was being discussed?",
  "Find something worth revisiting.",
];

function InlineMarkdown({
  children,
  moments,
  onOpenMoment,
}: {
  children: string;
  moments: Moment[];
  onOpenMoment: () => void;
}) {
  const parts = children.split(/(\[Moment\s+#\d+(?::[^\]]+)?\]|\*\*[^*]+\*\*)/gi);
  return parts.map((part, index) => {
    const citation = part.match(/^\[Moment\s+#(\d+)(?::[^\]]+)?\]$/i);
    if (citation) {
      const sequence = Number(citation[1]);
      const moment = moments.find((candidate) => candidate.sequence === sequence);
      const label = moment
        ? `Moment #${String(sequence).padStart(3, "0")}: ${momentTitle(moment)}`
        : `Moment #${String(sequence).padStart(3, "0")}`;
      return moment ? (
        <Link
          key={index}
          href={`/moment/${moment.id}`}
          onClick={onOpenMoment}
          className="mx-0.5 inline rounded-md border border-accent/25 bg-accent/10 px-1.5 py-0.5 font-medium text-accent underline decoration-accent/45 underline-offset-2 transition hover:border-accent/60 hover:bg-accent/20"
          title={`Open ${label}`}
        >
          {label}
        </Link>
      ) : (
        <span key={index} className="font-medium text-accent">{label}</span>
      );
    }
    return part.startsWith("**") && part.endsWith("**") ? (
      <strong key={index} className="font-semibold text-fg">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={index}>{part}</span>
    );
  });
}

function MarkdownAnswer({
  text,
  moments,
  onOpenMoment,
}: {
  text: string;
  moments: Moment[];
  onOpenMoment: () => void;
}) {
  const lines = text.replace(/[—–]/g, "-").split("\n");
  const rendered: ReactNode[] = [];
  lines.forEach((raw, index) => {
    const line = raw.trim();
    if (!line) {
      rendered.push(<div key={index} className="h-2" />);
      return;
    }
    if (/^[-*•]\s+/.test(line)) {
      rendered.push(
        <div key={index} className="flex gap-2.5 pl-1 text-sm leading-6 text-fg/85">
          <span className="mt-[1px] text-accent">•</span>
          <p><InlineMarkdown moments={moments} onOpenMoment={onOpenMoment}>{line.replace(/^[-*•]\s+/, "")}</InlineMarkdown></p>
        </div>,
      );
      return;
    }
    const heading = line.replace(/^#{1,4}\s+/, "");
    rendered.push(
      <p key={index} className={cn(
        "text-sm leading-6 text-fg/85",
        heading !== line && "pt-1 font-medium text-fg",
      )}>
        <InlineMarkdown moments={moments} onOpenMoment={onOpenMoment}>{heading}</InlineMarkdown>
      </p>,
    );
  });
  return <div>{rendered}</div>;
}

function encodeHistory(history: ConversationTurn[]) {
  const bytes = new TextEncoder().encode(JSON.stringify(history.slice(-8)));
  let binary = "";
  bytes.forEach((value) => { binary += String.fromCharCode(value); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function spokenVersion(text: string) {
  return text
    .replace(/\[Moment #[^\]]+\]/g, "")
    .replace(/[*#•]/g, "")
    .replace(/[—–]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

function VoiceGlyph({ state }: { state: VoiceState }) {
  if (state === "listening") {
    return <span className="h-3.5 w-3.5 rounded-[3px] bg-current" aria-hidden />;
  }
  if (state === "speaking") {
    return (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden>
        <path d="M5 10v4h3l4 3V7L8 10H5Z" fill="currentColor" />
        <path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a7.5 7.5 0 0 1 0 11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden>
      <rect x="8.5" y="3" width="7" height="12" rx="3.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3M9 21h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function MemoryGuard() {
  const { moments, selectedDate } = useMoments();
  // Starts minimized so the hero and gallery get the space; one tap opens it.
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState<GuardStatus>({});
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [result, setResult] = useState<GuardAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<ConversationTurn[]>([]);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const voiceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const voiceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const [voiceElapsed, setVoiceElapsed] = useState(0);

  useEffect(() => {
    fetch("/api/agent", { cache: "no-store" })
      .then(async (response) => ({ ...(await response.json()), offline: !response.ok }))
      .then(setStatus)
      .catch(() => setStatus({ offline: true }));
  }, []);

  useEffect(() => () => {
    if (voiceTimerRef.current) clearTimeout(voiceTimerRef.current);
    if (voiceIntervalRef.current) clearInterval(voiceIntervalRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.onstop = null;
      recorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    window.speechSynthesis?.cancel();
  }, []);

  useEffect(() => {
    if (!open) return;
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [busy, history, open, result, voiceState]);

  function rememberTurn(prompt: string, answer: string) {
    setHistory((current) => [...current,
      { role: "user", content: prompt },
      { role: "assistant", content: answer },
    ].slice(-8) as ConversationTurn[]);
  }

  function speak(answer: string) {
    if (!("speechSynthesis" in window)) {
      setVoiceState("idle");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(spokenVersion(answer));
    utterance.rate = 0.98;
    utterance.pitch = 1.02;
    const voices = window.speechSynthesis.getVoices();
    utterance.voice = voices.find((voice) =>
      voice.lang.toLowerCase().startsWith("en") &&
      /samantha|ava|allison|serena|daniel/i.test(voice.name),
    ) ?? voices.find((voice) => voice.lang.toLowerCase().startsWith("en")) ?? null;
    utterance.onstart = () => setVoiceState("speaking");
    utterance.onend = () => setVoiceState("idle");
    utterance.onerror = () => setVoiceState("idle");
    window.speechSynthesis.speak(utterance);
  }

  async function submitPrompt(rawPrompt: string) {
    const prompt = rawPrompt.trim();
    if (!prompt || busy) return;
    setQuestion("");
    setSubmittedQuestion(prompt);
    setBusy(true);
    setResult(null);
    try {
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt, date: selectedDate, history }),
      });
      const body = (await response.json()) as GuardAnswer;
      if (!response.ok) throw new Error(body.error || "Memory Guard could not answer");
      const normalized = { ...body, answer: body.answer.replace(/[—–]/g, "-") };
      setResult(normalized);
      rememberTurn(prompt, normalized.answer);
    } catch (error) {
      setResult({
        answer: error instanceof Error ? error.message : "Memory Guard could not answer",
        providerLabel: status.agent?.providerLabel ?? "Selected model",
        model: status.agent?.model ?? "offline",
        retrievalEngine: "unavailable",
        momentIds: [],
      });
    } finally {
      setBusy(false);
    }
  }

  function ask(event: FormEvent) {
    event.preventDefault();
    void submitPrompt(question);
  }

  async function sendVoice(blob: Blob) {
    setVoiceState("thinking");
    setBusy(true);
    setResult(null);
    try {
      const query = selectedDate ? `?date=${encodeURIComponent(selectedDate)}` : "";
      const response = await fetch(`/api/agent/voice${query}`, {
        method: "POST",
        headers: {
          "Content-Type": blob.type || "audio/webm",
          "X-Memory-History": encodeHistory(history),
        },
        body: blob,
      });
      const body = (await response.json()) as GuardAnswer;
      if (!response.ok) throw new Error(body.error || "Memory Guard could not hear that");
      const transcript = body.transcript?.trim();
      if (!transcript) throw new Error("Meta did not detect a spoken question");
      const normalized = { ...body, answer: body.answer.replace(/[—–]/g, "-") };
      setSubmittedQuestion(transcript);
      setResult(normalized);
      rememberTurn(transcript, normalized.answer);
      speak(normalized.answer);
    } catch (error) {
      setVoiceError(error instanceof Error ? error.message : "Voice chat failed");
      setVoiceState("error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleVoice() {
    if (voiceState === "listening") {
      if (voiceTimerRef.current) clearTimeout(voiceTimerRef.current);
      if (voiceIntervalRef.current) clearInterval(voiceIntervalRef.current);
      setVoiceState("thinking");
      recorderRef.current?.stop();
      return;
    }
    if (voiceState === "speaking") {
      window.speechSynthesis.cancel();
      setVoiceState("idle");
      return;
    }
    if (busy) return;
    setVoiceError("");
    window.speechSynthesis?.cancel();
    try {
      if (!("MediaRecorder" in window)) {
        throw new Error("This browser does not support microphone recording");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      });
      const preferred = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, preferred ? { mimeType: preferred } : undefined);
      const chunks: BlobPart[] = [];
      streamRef.current = stream;
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = () => {
        if (voiceTimerRef.current) clearTimeout(voiceTimerRef.current);
        if (voiceIntervalRef.current) clearInterval(voiceIntervalRef.current);
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        void sendVoice(blob);
      };
      recorder.start(250);
      setVoiceElapsed(0);
      setVoiceState("listening");
      const startedAt = Date.now();
      voiceIntervalRef.current = setInterval(() => {
        setVoiceElapsed(Math.min(30, Math.floor((Date.now() - startedAt) / 1000)));
      }, 250);
      voiceTimerRef.current = setTimeout(() => {
        if (recorder.state !== "inactive") {
          setVoiceState("thinking");
          recorder.stop();
        }
      }, 30_000);
    } catch (error) {
      setVoiceError(error instanceof Error ? error.message : "Microphone access failed");
      setVoiceState("error");
    }
  }

  const usingModel = Boolean(status.agent?.configured && !status.agent?.error);
  const provider = usingModel
    ? status.agent?.providerLabel ?? "Selected model"
    : "Local Memory Guard";
  const providerReady = Boolean(!status.offline && (usingModel || status.agent?.fallbackAvailable));
  const sources = useMemo(() => {
    return (result?.momentIds ?? []).flatMap((id) => {
      const moment = moments.find((candidate) => candidate.id === id);
      return moment ? [moment] : [];
    }).slice(0, 5);
  }, [moments, result?.momentIds]);
  const previousHistory = useMemo(() => {
    const currentIsCommitted = Boolean(
      result && history.at(-2)?.role === "user" &&
      history.at(-2)?.content === submittedQuestion,
    );
    return currentIsCommitted ? history.slice(0, -2) : history;
  }, [history, result, submittedQuestion]);

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
    <aside className={cn(
      "fixed right-0 z-50 flex overflow-hidden border-white/15 bg-[#111113]/94 shadow-[0_24px_90px_rgba(0,0,0,.65)] backdrop-blur-2xl transition-all duration-300",
      expanded
        ? "inset-y-0 w-full flex-col border-l sm:max-w-[640px]"
        : "bottom-5 right-5 h-[min(640px,calc(100dvh-2.5rem))] w-[calc(100%-2.5rem)] max-w-[410px] flex-col rounded-[28px] border lg:bottom-auto lg:top-24 lg:h-[min(640px,calc(100dvh-7rem))]",
    )}>
      <div className="shrink-0 border-b border-white/10 px-5 py-4">
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
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              className="rounded-full border border-white/10 px-2.5 py-1.5 text-[11px] text-fg-mute transition hover:border-accent/30 hover:bg-white/5 hover:text-fg"
              aria-label={expanded ? "Use compact Memory Guard" : "Expand Memory Guard"}
              aria-expanded={expanded}
              title={expanded ? "Return to compact chat" : "Open full-height chat"}
            >
              {expanded ? "Compact" : "Expand"}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-full px-2 py-1 text-lg leading-none text-fg-mute transition hover:bg-white/5 hover:text-fg"
              aria-label="Minimize Memory Guard"
            >
              −
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-[10px] tracking-[0.12em] uppercase">
          <span className={`rounded-full border px-2.5 py-1 ${providerReady ? "border-ok/30 bg-ok/10 text-ok" : "border-white/10 text-fg-mute"}`}>
            {providerReady ? (usingModel ? "Agent ready" : "Grounded local") : "Agent offline"}
          </span>
          <span className="rounded-full border border-white/10 px-2.5 py-1 text-fg-dim">
            {status.elastic?.configured ? "Pre-indexed Elastic" : "Local retrieval"}
          </span>
          <span className="rounded-full border border-white/10 px-2.5 py-1 text-fg-dim">
            {status.voice?.configured ? "Meta voice ready" : "Voice unavailable"}
          </span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 px-5 py-5">
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1 overscroll-contain">
          {previousHistory.map((turn, index) => (
            turn.role === "user" ? (
              <div
                key={`${turn.role}-${index}`}
                className="ml-auto max-w-[88%] rounded-2xl rounded-tr-md bg-accent px-4 py-3 text-sm leading-6 text-bg"
              >
                {turn.content}
              </div>
            ) : (
              <div
                key={`${turn.role}-${index}`}
                className="rounded-2xl border border-white/10 bg-black/15 p-4 opacity-75"
              >
                <MarkdownAnswer
                  text={turn.content}
                  moments={moments}
                  onOpenMoment={() => { setExpanded(false); setOpen(false); }}
                />
              </div>
            )
          ))}
          {!submittedQuestion ? (
            <>
              <p className="text-sm leading-6 text-fg-dim">
                Ask across {selectedDate ? `moments from ${formatDateKey(selectedDate)}` : "all captured moments"}, visual context, and spike intensity.
              </p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    disabled={busy}
                    onClick={() => void submitPrompt(suggestion)}
                    className="rounded-full border border-white/10 bg-white/[.035] px-3 py-1.5 text-left text-[11px] text-fg-dim transition hover:border-accent/30 hover:text-fg disabled:opacity-40"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="ml-auto max-w-[88%] rounded-2xl rounded-tr-md bg-accent px-4 py-3 text-sm leading-6 text-bg">
              {submittedQuestion}
            </div>
          )}

          {busy ? (
            <div role="status" className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="flex items-center gap-3 text-sm text-fg/80">
                <span className="pulse-dot h-2 w-2 rounded-full bg-accent" />
                {voiceState === "thinking"
                  ? "Meta heard you. Searching your memories and preparing a reply…"
                  : "Searching pre-indexed memories, then writing your answer…"}
              </div>
            </div>
          ) : null}

          {voiceState === "listening" || voiceState === "speaking" ? (
            <div className="rounded-[26px] border border-accent/25 bg-accent/[.07] p-5 text-center">
              <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full border border-accent/30 bg-accent/10 shadow-[0_0_55px_rgba(122,109,255,.28)]">
                <div className="flex h-10 items-center gap-1" aria-hidden>
                  {[14, 28, 38, 24, 34, 18].map((height, index) => (
                    <span
                      key={index}
                      className="w-1 animate-pulse rounded-full bg-accent"
                      style={{ height, animationDelay: `${index * 90}ms` }}
                    />
                  ))}
                </div>
              </div>
              <p className="mt-4 text-base font-medium text-fg">
                {voiceState === "listening" ? "I’m listening" : "Memory Guard is speaking"}
              </p>
              <p className="mt-1 text-xs text-fg-mute">
                {voiceState === "listening"
                  ? `Speak naturally · ${voiceElapsed}s of 30s · tap Stop when finished`
                  : "Tap the voice button to interrupt"}
              </p>
            </div>
          ) : null}

          {voiceState === "error" && voiceError ? (
            <div className="rounded-2xl border border-error/25 bg-error/10 p-3 text-sm text-error">
              {voiceError}
            </div>
          ) : null}

          {result ? (
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <MarkdownAnswer
                text={result.answer}
                moments={moments}
                onOpenMoment={() => { setExpanded(false); setOpen(false); }}
              />
              {sources.length ? (
                <div className="mt-5 border-t border-white/10 pt-4">
                  <p className="text-[10px] tracking-[0.14em] text-fg-mute uppercase">
                    Video references
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {sources.map((moment) => (
                      <Link
                        key={moment.id}
                        href={`/moment/${moment.id}`}
                        onClick={() => {
                          setExpanded(false);
                          setOpen(false);
                        }}
                        className="inline-flex max-w-full items-center gap-2 rounded-full border border-accent/25 bg-accent/[.07] px-3 py-2 text-xs text-fg transition hover:border-accent/60 hover:bg-accent/[.12]"
                      >
                        <span aria-hidden>▶</span>
                        <span className="truncate">Moment #{String(moment.sequence).padStart(3, "0")} · {momentTitle(moment)}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              ) : null}
              <p className="mt-4 text-[10px] tracking-[0.12em] text-fg-mute uppercase">
                {result.providerLabel} · {result.retrievalEngine}
              </p>
            </div>
          ) : null}
          <div ref={chatEndRef} aria-hidden />
        </div>

        <div className="shrink-0 border-t border-white/10 pt-4">
          <form onSubmit={ask} className="flex gap-2">
            <label className="sr-only" htmlFor="memory-guard-question">Ask Memory Guard</label>
            <input
              id="memory-guard-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={2000}
              placeholder="Ask about your day…"
              className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-white/[.045] px-4 py-3 text-sm text-fg placeholder:text-fg-mute focus:border-accent/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => void toggleVoice()}
              disabled={busy && voiceState !== "listening"}
              className={cn(
                "flex h-12 shrink-0 items-center justify-center gap-2 rounded-2xl border px-3 text-lg transition disabled:cursor-not-allowed disabled:opacity-40",
                voiceState === "listening"
                  ? "border-error/50 bg-error text-white shadow-[0_0_28px_rgba(255,89,112,.3)]"
                  : voiceState === "speaking"
                    ? "border-accent/50 bg-accent text-bg"
                    : "border-white/10 bg-white/[.045] text-fg hover:border-accent/50 hover:bg-accent/10",
              )}
              aria-label={voiceState === "listening" ? "Stop recording and send" :
                voiceState === "speaking" ? "Stop spoken response" : "Start voice conversation"}
              title={voiceState === "listening" ? "Stop and send" : "Voice conversation"}
            >
              <VoiceGlyph state={voiceState} />
              <span className="text-xs font-medium">
                {voiceState === "listening" ? "Stop" : voiceState === "speaking" ? "Mute" : "Talk"}
              </span>
            </button>
            <button
              type="submit"
              disabled={!question.trim() || busy}
              className="rounded-2xl bg-fg px-4 py-3 text-sm font-medium text-bg transition hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? "…" : "Ask"}
            </button>
          </form>
          <p className="mt-2 px-1 text-[11px] leading-4 text-fg-mute">
            {voiceState === "listening"
              ? `Listening now · ${voiceElapsed}s / 30s · tap Stop to send`
              : voiceState === "thinking"
                ? "Meta heard you · Elastic is finding the memory · Memory Guard is replying"
                : voiceState === "speaking"
                  ? "Speaking the answer · tap Mute to interrupt"
                  : "Type and press Ask, or tap Talk · speak · tap Stop"}
          </p>
        </div>
      </div>
    </aside>
  );
}
