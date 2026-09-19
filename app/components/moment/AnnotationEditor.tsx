"use client";

import { useState } from "react";
import { useMoments } from "@/context/MomentsProvider";
import type { Moment } from "@/types/moment";

export function AnnotationEditor({ moment }: { moment: Moment }) {
  const { updateMoment } = useMoments();
  const [value, setValue] = useState(moment.annotation);
  const [saved, setSaved] = useState(false);

  const dirty = value !== moment.annotation;

  return (
    <section className="border border-line bg-bg-panel p-5 md:p-6">
      <label
        htmlFor="annotation"
        className="text-[11px] tracking-[0.2em] uppercase text-fg-dim"
      >
        What happened?
      </label>
      <p className="mt-2 text-sm text-fg-mute">
        A personal note about the surrounding context. Optional.
      </p>
      <textarea
        id="annotation"
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          setSaved(false);
        }}
        rows={4}
        placeholder="I finally understood why the result was negative."
        className="mt-4 w-full resize-y border border-line-strong bg-transparent px-3 py-3 text-sm leading-6 text-fg outline-none placeholder:text-fg-mute focus:border-accent"
      />
      <div className="mt-4 flex items-center gap-4">
        <button
          type="button"
          disabled={!dirty}
          onClick={() => {
            updateMoment(moment.id, { annotation: value.trim() });
            setSaved(true);
          }}
          className="border border-accent/50 px-4 py-2 text-[11px] tracking-[0.18em] uppercase text-accent transition-colors enabled:hover:bg-accent enabled:hover:text-bg disabled:cursor-not-allowed disabled:opacity-35"
        >
          Save annotation
        </button>
        {saved ? (
          <span className="text-[12px] text-ok">Saved</span>
        ) : dirty ? (
          <span className="text-[12px] text-fg-mute">Unsaved changes</span>
        ) : null}
      </div>
    </section>
  );
}
