"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

/**
 * Visual oddball task for calibrating the detector's dynamic range.
 *
 * A predictable count (the standard) is interrupted, on a minority of trials, by a
 * letter (the target). Targets evoke a P300; standards do not. Recording EEG through a
 * block therefore yields the response floor (standards) and ceiling (targets) for this
 * wearer, on this day — the two numbers a threshold has to sit between.
 *
 * Parameters follow Decoding P300 as a shared neural mechanism for oddball target
 * detection and working memory updating (PMC12907112): 30% targets, each stimulus shown
 * for 500 ms then a fixation cross for 1500 ms, a button press on targets, P300 read at
 * Pz in the 250–650 ms window. The paper used X/O; counting numbers versus letters keeps
 * the same standard/deviant structure with a more legible standard.
 *
 * Every onset is sent to the backend as a marker so EEG windows can be labelled after
 * the fact. Timestamps are recorded here too and exportable, in case the backend is off.
 */

const STIMULUS_MS = 500;
const FIXATION_MS = 1500;
const TARGET_PROBABILITY = 0.3;
const DEFAULT_TRIALS = 60;
const PAPER_TRIALS = 180;
const RESPONSE_WINDOW_MS = STIMULUS_MS + FIXATION_MS;
const LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ";

type Kind = "standard" | "target";
type Phase = "idle" | "countdown" | "running" | "done";

interface Trial {
  index: number;
  kind: Kind;
  stimulus: string;
  onsetMs: number;
  onsetIso: string;
  responseMs: number | null;
}

function buildSequence(count: number): { kind: Kind; stimulus: string }[] {
  const sequence: { kind: Kind; stimulus: string }[] = [];
  let number = 1;
  for (let i = 0; i < count; i += 1) {
    // Never open on a target: the first stimulus has no expectation to violate.
    const isTarget = i > 0 && Math.random() < TARGET_PROBABILITY;
    if (isTarget) {
      sequence.push({ kind: "target", stimulus: LETTERS[Math.floor(Math.random() * LETTERS.length)] });
    } else {
      sequence.push({ kind: "standard", stimulus: String(number) });
      number += 1;
    }
  }
  return sequence;
}

function postMarker(label: string, detail: Record<string, unknown>) {
  // Fire-and-forget on purpose: awaiting this would put network latency inside the
  // stimulus schedule. The onset time is already captured before this is called.
  void fetch("/api/markers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, detail }),
    keepalive: true,
  }).catch(() => undefined);
}

export function OddballCalibration() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [trialCount, setTrialCount] = useState(DEFAULT_TRIALS);
  const [countdown, setCountdown] = useState(3);
  const [current, setCurrent] = useState<{ kind: Kind; stimulus: string } | null>(null);
  const [trials, setTrials] = useState<Trial[]>([]);
  const [flash, setFlash] = useState(false);
  const [progress, setProgress] = useState({ index: 0, total: 0 });

  const sequence = useRef<{ kind: Kind; stimulus: string }[]>([]);
  const position = useRef(0);
  const timers = useRef<number[]>([]);
  const live = useRef<Trial | null>(null);
  const sessionId = useRef<string>("");
  const originMs = useRef(0);
  const advance = useRef<() => void>(() => undefined);

  const clearTimers = () => {
    timers.current.forEach(window.clearTimeout);
    timers.current = [];
  };

  const finish = useCallback(() => {
    clearTimers();
    setCurrent(null);
    setPhase("done");
    postMarker("calibration_end", { session: sessionId.current, trials: sequence.current.length });
  }, []);

  const respond = useCallback(() => {
    const trial = live.current;
    if (!trial || trial.responseMs !== null) return;
    const elapsed = performance.now() - originMs.current - trial.onsetMs;
    if (elapsed > RESPONSE_WINDOW_MS) return;
    trial.responseMs = Math.round(elapsed);
    setFlash(true);
    window.setTimeout(() => setFlash(false), 120);
    setTrials((all) => all.map((t) => (t.index === trial.index ? { ...trial } : t)));
  }, []);

  const showNext = useCallback(() => {
    const index = position.current;
    if (index >= sequence.current.length) {
      finish();
      return;
    }
    const item = sequence.current[index];
    const onsetMs = performance.now() - originMs.current;
    const trial: Trial = {
      index,
      kind: item.kind,
      stimulus: item.stimulus,
      onsetMs: Math.round(onsetMs),
      onsetIso: new Date().toISOString(),
      responseMs: null,
    };
    live.current = trial;
    setCurrent(item);
    setProgress({ index: index + 1, total: sequence.current.length });
    setTrials((all) => [...all, trial]);
    postMarker(item.kind === "target" ? "oddball_target" : "oddball_standard", {
      session: sessionId.current,
      trial: index,
      stimulus: item.stimulus,
      onset_ms: trial.onsetMs,
      onset_iso: trial.onsetIso,
    });

    timers.current.push(window.setTimeout(() => setCurrent(null), STIMULUS_MS));
    timers.current.push(window.setTimeout(() => {
      position.current = index + 1;
      advance.current();
    }, STIMULUS_MS + FIXATION_MS));
  }, [finish]);

  useEffect(() => {
    advance.current = showNext;
  }, [showNext]);

  const start = useCallback(() => {
    clearTimers();
    sequence.current = buildSequence(trialCount);
    position.current = 0;
    live.current = null;
    sessionId.current = `oddball-${Date.now().toString(36)}`;
    setTrials([]);
    setCurrent(null);
    setCountdown(3);
    setPhase("countdown");

    let remaining = 3;
    const tick = window.setInterval(() => {
      remaining -= 1;
      setCountdown(remaining);
      if (remaining <= 0) {
        window.clearInterval(tick);
        originMs.current = performance.now();
        postMarker("calibration_start", {
          session: sessionId.current,
          trials: trialCount,
          target_probability: TARGET_PROBABILITY,
          stimulus_ms: STIMULUS_MS,
          fixation_ms: FIXATION_MS,
          reference: "PMC12907112",
        });
        setPhase("running");
        showNext();
      }
    }, 1000);
    timers.current.push(tick as unknown as number);
  }, [showNext, trialCount]);

  const stop = useCallback(() => {
    if (phase === "running" || phase === "countdown") finish();
  }, [finish, phase]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space") return;
      if (phase !== "running") return;
      event.preventDefault();
      respond();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, respond]);

  useEffect(() => () => clearTimers(), []);

  const targets = trials.filter((t) => t.kind === "target");
  const standards = trials.filter((t) => t.kind === "standard");
  const hits = targets.filter((t) => t.responseMs !== null);
  const falseAlarms = standards.filter((t) => t.responseMs !== null);
  const meanRt = hits.length
    ? Math.round(hits.reduce((sum, t) => sum + (t.responseMs ?? 0), 0) / hits.length)
    : null;

  const exportJson = () => {
    const payload = {
      session: sessionId.current,
      reference: "PMC12907112",
      parameters: {
        trials: sequence.current.length,
        target_probability: TARGET_PROBABILITY,
        stimulus_ms: STIMULUS_MS,
        fixation_ms: FIXATION_MS,
      },
      summary: {
        targets: targets.length,
        standards: standards.length,
        hits: hits.length,
        misses: targets.length - hits.length,
        false_alarms: falseAlarms.length,
        mean_rt_ms: meanRt,
      },
      trials,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sessionId.current || "oddball"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const running = phase === "running" || phase === "countdown";

  return (
    <section className="mb-10 border border-line bg-bg-panel">
      <div className="border-b border-line px-5 py-3">
        <h2 className="text-[11px] tracking-[0.2em] uppercase text-fg-dim">
          Calibration · visual oddball
        </h2>
        <p className="mt-2 max-w-xl text-[12px] leading-5 text-fg-mute">
          A count runs up; now and then a letter appears instead. Press <kbd className="rounded border border-line-strong px-1 font-mono text-[11px]">space</kbd> (or tap
          the stage) only on letters. Letters are rare, so they evoke the large response;
          numbers evoke the small one. Recording EEG through a block gives the floor and
          ceiling a detection threshold must sit between. 30% targets, 500 ms on, 1500 ms
          fixation — after PMC12907112.
        </p>
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={phase === "running" ? respond : undefined}
        onKeyDown={(e) => { if (e.code === "Space" && phase === "running") { e.preventDefault(); respond(); } }}
        className={cn(
          "relative flex h-72 select-none items-center justify-center bg-black transition-colors duration-100",
          flash && "bg-[#1a1a1a]",
          phase === "running" && "cursor-pointer",
        )}
        aria-label="Oddball stage"
      >
        {phase === "idle" || phase === "done" ? (
          <p className="px-6 text-center text-sm text-fg-mute">
            {phase === "done" ? "Block complete." : "Ready. Fix your gaze on the centre."}
          </p>
        ) : null}

        {phase === "countdown" ? (
          <p className="font-mono text-7xl text-fg-dim">{countdown || "·"}</p>
        ) : null}

        {phase === "running" ? (
          current ? (
            <p
              className={cn(
                "font-mono leading-none",
                current.kind === "target"
                  ? "text-[9rem] text-fg"
                  : "text-[9rem] text-fg",
              )}
            >
              {current.stimulus}
            </p>
          ) : (
            <p className="font-mono text-6xl text-fg-mute" aria-hidden>+</p>
          )
        ) : null}

        {phase === "running" ? (
          <p className="absolute bottom-3 right-4 font-mono text-[11px] text-fg-mute">
            {progress.index} / {progress.total}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-line px-5 py-4">
        {!running ? (
          <>
            <button
              type="button"
              onClick={start}
              className="border border-accent/60 px-5 py-2.5 text-[11px] tracking-[0.2em] uppercase text-accent transition-colors hover:bg-accent hover:text-bg"
            >
              {phase === "done" ? "Run another block" : "Start block"}
            </button>
            <label className="flex items-center gap-2 font-mono text-[11px] text-fg-dim">
              trials
              <select
                value={trialCount}
                onChange={(e) => setTrialCount(Number(e.target.value))}
                className="border border-line-strong bg-bg px-2 py-1 text-fg"
              >
                <option value={30}>30 · quick (1 min)</option>
                <option value={60}>60 · default (2 min)</option>
                <option value={PAPER_TRIALS}>180 · as in the paper (6 min)</option>
              </select>
            </label>
          </>
        ) : (
          <button
            type="button"
            onClick={stop}
            className="border border-error/60 px-5 py-2.5 text-[11px] tracking-[0.2em] uppercase text-error transition-colors hover:bg-error hover:text-bg"
          >
            Stop block
          </button>
        )}
        {phase === "done" ? (
          <button
            type="button"
            onClick={exportJson}
            className="text-[11px] tracking-[0.2em] uppercase text-fg-dim underline hover:text-fg"
          >
            Export trials (JSON)
          </button>
        ) : null}
      </div>

      {trials.length > 0 ? (
        <div className="grid grid-cols-2 gap-px border-t border-line bg-line sm:grid-cols-5">
          {[
            ["targets", `${targets.length}`],
            ["hits", `${hits.length} / ${targets.length}`],
            ["false alarms", `${falseAlarms.length}`],
            ["mean RT", meanRt !== null ? `${meanRt} ms` : "—"],
            ["standards", `${standards.length}`],
          ].map(([label, value]) => (
            <div key={label} className="bg-bg-panel px-4 py-3">
              <p className="text-[10px] tracking-[0.16em] uppercase text-fg-mute">{label}</p>
              <p className="mt-1 font-mono text-sm text-fg">{value}</p>
            </div>
          ))}
        </div>
      ) : null}

      {phase === "done" ? (
        <p className="border-t border-line px-5 py-3 text-[12px] leading-5 text-fg-mute">
          Each onset was sent to the backend as an <code className="font-mono">oddball_target</code> or{" "}
          <code className="font-mono">oddball_standard</code> marker with its timestamp, so EEG
          windows in this session&apos;s <code className="font-mono">events.jsonl</code> can be
          labelled. Compare the detector&apos;s z-scores in the 250–650 ms window after targets
          against standards: that spread is this wearer&apos;s dynamic range today.
        </p>
      ) : null}
    </section>
  );
}
