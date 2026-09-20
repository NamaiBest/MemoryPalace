"use client";

import Link from "next/link";

/**
 * The evidence behind the trigger, for anyone who asks "does this actually work".
 *
 * Static on purpose. These are published results from two public datasets, recomputed
 * once from the committed model outputs, not something the running backend measures. The
 * numbers live here rather than behind an API so the page cannot quietly disagree with
 * the repository.
 */

const ELECTRODES = [
  { count: 16, where: "Full scalp", auc: 84, best10: 95, glasses: false },
  { count: 8, where: "Scalp, Crown-like", auc: 82, best10: 92, glasses: false },
  { count: 2, where: "Fz, Cz", auc: 76, best10: 93, glasses: false },
  { count: 4, where: "Fz Cz F7 F8", auc: 76, best10: 91, glasses: false },
  { count: 2, where: "F3, F4", auc: 73, best10: 87, glasses: false },
  { count: 4, where: "On glasses", auc: 65, best10: 78, glasses: true },
  { count: 2, where: "Glasses brow", auc: 63, best10: 77, glasses: true },
  { count: 2, where: "Glasses temples", auc: 61, best10: 75, glasses: true },
];

const PEOPLE = [
  { id: "VP002", auc: 93, beat: 3 },
  { id: "VP005", auc: 89, beat: 2 },
  { id: "VP003", auc: 80, beat: 1 },
  { id: "VP006", auc: 67, beat: 1 },
  { id: "VP004", auc: 65, beat: 1 },
];

/** One row of a bar chart. Bars start at 50 because 50 is chance, not zero. */
function Bar({ value, tone }: { value: number; tone: "scalp" | "glasses" | "person" }) {
  const pct = ((value - 50) / 50) * 100;
  const color =
    tone === "glasses" ? "var(--color-error)"
      : tone === "person" ? "var(--color-insight)"
        : "var(--color-accent)";
  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
      <div
        className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
        style={{ width: `${Math.max(2, pct)}%`, backgroundColor: color }}
      />
    </div>
  );
}

function Figure({ value, unit = "%" }: { value: number; unit?: string }) {
  return (
    <span className="font-mono text-sm tabular-nums text-fg">
      {value}
      <span className="text-fg-mute">{unit}</span>
    </span>
  );
}

export function StatsPage() {
  return (
    <main className="mx-auto w-full max-w-[1100px] px-6 pb-24 pt-32 md:px-12">
      <Link href="/debug" className="font-mono text-[11px] tracking-[0.2em] uppercase text-accent hover:text-fg">
        ← Debug
      </Link>
      <h1 className="mt-5 max-w-3xl text-balance font-serif text-5xl leading-[1.12] md:text-6xl">
        Does it actually work?
      </h1>
      <p className="mt-6 max-w-2xl text-base leading-8 text-fg-dim">
        Two questions, two public datasets. MemoryPalace triggers on a sustained deviation
        from your own baseline, never an instantaneous spike. We tested brief spikes
        against a null that could have proved us wrong, and it did.
      </p>

      {/* headline */}
      <div className="mt-12 grid gap-4 sm:grid-cols-3">
        {[
          { n: "84%", l: "16 electrodes", s: "spotting a surprise" },
          { n: "82%", l: "8 electrodes", s: "half the hardware, 2 points" },
          { n: "61%", l: "2 on glasses", s: "barely above chance" },
        ].map((card, i) => (
          <div
            key={card.l}
            className={`rounded-2xl border px-6 py-7 ${
              i === 2 ? "border-error/30 bg-error/[0.06]" : "border-line bg-bg-raised/60"
            }`}
          >
            <p className={`font-serif text-4xl ${i === 2 ? "text-error" : "text-fg"}`}>{card.n}</p>
            <p className="mt-2 text-sm text-fg">{card.l}</p>
            <p className="mt-1 text-xs text-fg-mute">{card.s}</p>
          </div>
        ))}
      </div>

      {/* electrodes */}
      <section className="mt-16">
        <h2 className="font-serif text-3xl">Where the electrodes sit beats how many</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-fg-dim">
          Spotting a surprise, calibrated per person, on 38 recordings from a public
          16-channel dataset. Two electrodes at Fz and Cz beat four on glasses. The
          information simply is not present at glasses positions.
        </p>

        <div className="mt-8 overflow-hidden rounded-2xl border border-line">
          <div className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-5 border-b border-line bg-bg-raised/60 px-5 py-3 font-mono text-[10px] tracking-[0.16em] uppercase text-fg-mute">
            <span>Electrodes</span><span>Placement</span>
            <span className="text-right">Average</span><span className="text-right">Best 10</span>
          </div>
          {ELECTRODES.map((row, i) => (
            <div
              key={`${row.count}-${row.where}`}
              className={`grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-5 px-5 py-4 ${
                i % 2 ? "bg-white/[0.015]" : ""
              }`}
            >
              <span className="w-8 text-right font-serif text-2xl text-fg">{row.count}</span>
              <span className="min-w-0">
                <span className={`block truncate text-sm ${row.glasses ? "text-error" : "text-fg"}`}>
                  {row.where}
                </span>
                <span className="mt-2 block max-w-[320px]">
                  <Bar value={row.auc} tone={row.glasses ? "glasses" : "scalp"} />
                </span>
              </span>
              <span className="text-right"><Figure value={row.auc} /></span>
              <span className="text-right font-mono text-sm tabular-nums text-fg-mute">
                {row.best10}%
              </span>
            </div>
          ))}
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <p className="rounded-xl border border-accent/25 bg-accent/[0.07] px-5 py-4 text-sm leading-6 text-fg">
            Halving the electrodes, 16 to 8, costs <strong>2 points</strong>.
          </p>
          <p className="rounded-xl border border-error/25 bg-error/[0.07] px-5 py-4 text-sm leading-6 text-fg">
            Moving them to the temples costs <strong>21 points</strong>.
          </p>
        </div>
      </section>

      {/* people */}
      <section className="mt-16">
        <h2 className="font-serif text-3xl">Every brain is different</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-fg-dim">
          Spotting a sustained focused state, 5 participants, 3 sessions each. Calibrated
          on the first six blocks and scored on the last three, with the model frozen
          before scoring. The spread is the whole argument for training per person.
        </p>

        <div className="mt-8 overflow-hidden rounded-2xl border border-line">
          <div className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-5 border-b border-line bg-bg-raised/60 px-5 py-3 font-mono text-[10px] tracking-[0.16em] uppercase text-fg-mute">
            <span>Person</span><span>Accuracy</span>
            <span className="text-right">AUC</span><span className="text-right">Sessions</span>
          </div>
          {PEOPLE.map((row, i) => (
            <div
              key={row.id}
              className={`grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-5 px-5 py-4 ${
                i % 2 ? "bg-white/[0.015]" : ""
              }`}
            >
              <span className="w-16 font-mono text-sm text-fg">{row.id}</span>
              <span className="max-w-[360px]"><Bar value={row.auc} tone="person" /></span>
              <span className="text-right"><Figure value={row.auc} /></span>
              <span className="text-right font-mono text-sm tabular-nums text-fg-mute">
                {row.beat}/3
              </span>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm leading-7 text-fg-dim">
          Across all 15 sessions the average is <strong className="text-fg">79%</strong>,
          with 14 of 15 above chance and 8 beating their own statistical null. Across
          those 8 it is <strong className="text-fg">91%</strong>.
        </p>
      </section>

      {/* limits */}
      <section className="mt-16 rounded-2xl border border-line bg-bg-raised/40 px-6 py-7 md:px-8">
        <h2 className="font-serif text-2xl">What these numbers are not</h2>
        <ul className="mt-5 space-y-3 text-sm leading-7 text-fg-dim">
          <li>
            <strong className="text-fg">AUC is not accuracy.</strong> It is how often the
            model ranks the right window higher. Balanced accuracy is 71% overall.
          </li>
          <li>
            The label is <strong className="text-fg">task versus rest</strong>, a proxy for
            a state change. Not confusion, not emotion, and we never call it that.
          </li>
          <li>Weights do not transfer between people or sessions.</li>
          <li>
            <strong className="text-fg">The live demo has never detected anything in a
            real wearer.</strong> Every end to end run used synthetic EEG. These results
            say the signal is real in public data.
          </li>
        </ul>
      </section>
    </main>
  );
}
