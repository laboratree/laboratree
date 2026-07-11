"use client";

import { useState } from "react";
import type { ParamSpec } from "@/lib/api";

/** Collapsible hyperparameter panel — sliders/selects seeded from the paper's settings; editing
 *  re-fits the model live. Shared by the guided lesson player and the classic staged view. */
export function ParamPanel({
  spec,
  paperDefaults,
  onChange,
  onReset,
  onSaveVariant,
}: {
  spec: ParamSpec[];
  paperDefaults?: Record<string, number | string | string[]>;
  onChange: (key: string, value: number | string) => void;
  onReset: () => void;
  onSaveVariant?: () => void;
}) {
  const [open, setOpen] = useState(false);
  if (!spec.length) return null;
  // a knob is "tweaked" when it differs from what the paper (or the library) defaults to
  const dirty = spec.some((s) => {
    const base = paperDefaults?.[s.key] ?? s.default;
    return String(s.value) !== String(base);
  });

  return (
    <div className="mb-2 rounded-lg border border-line bg-white/70">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-1.5 text-[11px] font-medium text-forest"
      >
        <span>
          ⚙ Hyperparameters{" "}
          <span className="font-normal text-muted">
            — {spec.map((s) => `${s.label} ${s.value}`).join(" · ")}
          </span>
        </span>
        <span className="flex items-center gap-2">
          {dirty && <span className="rounded-full bg-amber-100 px-1.5 text-[10px] text-amber-800">tweaked</span>}
          <span className="text-muted">{open ? "▲" : "▼"}</span>
        </span>
      </button>

      {open && (
        <div className="space-y-2.5 border-t border-line px-3 py-2.5">
          <p className="text-[10px] text-muted">
            Defaults follow the paper; drag to explore how each setting changes the model, then watch
            Training/Testing re-fit on the real data.
          </p>
          {spec.map((s) => (
            <ParamControl key={s.key} s={s} onChange={onChange} />
          ))}
          {dirty && (
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={onReset}
                className="rounded border border-line px-2 py-0.5 text-[11px] text-forest hover:bg-bg"
              >
                ↺ Reset to paper defaults
              </button>
              {onSaveVariant && (
                <button
                  onClick={onSaveVariant}
                  className="rounded bg-forest px-2 py-0.5 text-[11px] font-medium text-white hover:opacity-90"
                  title="Keep the paper's model AND add these settings as a separate branch to compare on the leaderboard"
                >
                  ⊕ Compare as new model branch
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ParamControl({
  s,
  onChange,
}: {
  s: ParamSpec;
  onChange: (key: string, value: number | string) => void;
}) {
  return (
    <label className="block" title={s.help}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-ink">{s.label}</span>
        <span className="font-mono text-forest">{s.value}</span>
      </div>
      {s.type === "select" ? (
        <select
          className="mt-1 w-full rounded border border-line px-2 py-1 text-xs"
          value={String(s.value)}
          onChange={(e) => onChange(s.key, e.target.value)}
        >
          {(s.options ?? []).map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      ) : (
        <input
          type="range"
          className="mt-1 w-full accent-leaf"
          min={s.min}
          max={s.max}
          step={s.step ?? (s.type === "int" ? 1 : 0.01)}
          value={Number(s.value)}
          onChange={(e) =>
            onChange(s.key, s.type === "int" ? Math.round(Number(e.target.value)) : Number(e.target.value))
          }
        />
      )}
      {s.help && <p className="mt-0.5 text-[10px] text-muted">{s.help}</p>}
    </label>
  );
}
