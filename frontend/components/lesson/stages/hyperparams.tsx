"use client";

import type { FactsHyperparam, ParamSpec } from "@/lib/api";
import type { LessonStageProps } from "./types";

/** Every knob the model exposes: plain meaning, effect, typical range — merged from the
 *  curated facts registry and the live param spec (which carries the current value). */
export default function HyperparamsStage({ lesson }: LessonStageProps) {
  const spec = lesson.param_spec ?? lesson.trace.param_spec ?? [];
  const docs = new Map<string, FactsHyperparam>(
    (lesson.facts?.hyperparameters ?? []).map((h) => [h.name, h]),
  );
  // knobs the full model exposes but this teaching fit keeps fixed (documented in facts only)
  const specKeys = new Set(spec.map((s) => s.key));
  const factsOnly = (lesson.facts?.hyperparameters ?? []).filter((h) => !specKeys.has(h.name));
  if (!spec.length && !factsOnly.length)
    return <p className="text-xs text-muted">This model has no tunable hyperparameters.</p>;

  return (
    <div>
      <div className="grid gap-1.5 sm:grid-cols-2">
        {spec.map((s: ParamSpec) => {
          const d = docs.get(s.key);
          return (
            <div key={s.key} className="rounded-lg border border-line bg-white px-2.5 py-2">
              <div className="flex items-baseline justify-between">
                <p className="text-[12px] font-medium text-forest">{s.label}</p>
                <span className="font-mono text-[11px] text-[#8a6d1a]">now {String(s.value)}</span>
              </div>
              <p className="mt-0.5 text-[11px] text-muted">{d?.plain ?? s.help ?? ""}</p>
              {d?.effect && <p className="mt-0.5 text-[11px] text-ink">{d.effect}</p>}
              <div className="mt-1 flex gap-2 font-mono text-[10px] text-muted">
                {d?.typical_range && <span>typical {d.typical_range}</span>}
                {s.min != null && s.max != null && (
                  <span>
                    range {s.min}–{s.max}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {factsOnly.length > 0 && (
        <>
          <p className="mb-1 mt-2.5 text-[10px] font-medium uppercase tracking-wide text-muted">
            Also on the full model (fixed in this demo)
          </p>
          <div className="grid gap-1.5 sm:grid-cols-2">
            {factsOnly.map((d) => (
              <div key={d.name} className="rounded-lg border border-dashed border-line bg-bg px-2.5 py-2">
                <p className="text-[12px] font-medium text-forest">{d.name}</p>
                <p className="mt-0.5 text-[11px] text-muted">{d.plain}</p>
                <p className="mt-0.5 text-[11px] text-ink">{d.effect}</p>
                {d.typical_range && (
                  <p className="mt-1 font-mono text-[10px] text-muted">typical {d.typical_range}</p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
      {spec.length > 0 && (
        <p className="mt-2 rounded border border-[#C9A227]/40 bg-[#FFFDF5] px-2 py-1.5 text-[11px] text-[#8a6d1a]">
          Open the ⚙ Hyperparameters panel above and drag any knob — the whole lesson re-fits on
          the real data so you can watch the effect.
        </p>
      )}
    </div>
  );
}
