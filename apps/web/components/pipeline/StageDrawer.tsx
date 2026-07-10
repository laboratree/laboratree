"use client";

import { useMemo, useState } from "react";
import { labTabLabel, type LabTabKey } from "@/lib/labTabs";
import { CUSTOM_PHASE, type FlowPhase } from "@/lib/pipelineTemplates";
import type { ComponentSpecLite } from "@/lib/api";
import ProvenanceBadge from "@/components/ProvenanceBadge";
import { KIND_META, stageStatusMeta, type StageState } from "./types";

export type StageDrawerProps = {
  stages: StageState[];
  phases: FlowPhase[];
  selectedId: string;
  components: ComponentSpecLite[];
  onPatch: (id: string, patch: Partial<StageState>) => void;
  onRemove: (id: string) => void;
  onSelect: (id: string) => void;
  onOpenLab?: (tab: LabTabKey) => void;
};

export default function StageDrawer({
  stages, phases, selectedId, components, onPatch, onRemove, onSelect, onOpenLab,
}: StageDrawerProps) {
  const [paramsError, setParamsError] = useState<string | null>(null);
  const [showAllComponents, setShowAllComponents] = useState(false);

  const index = stages.findIndex((s) => s.id === selectedId);
  const stage = index >= 0 ? stages[index] : null;

  // Task-specific picker: a stage's curated suggestions (plus its current pick) unless the
  // user asks for the full registry.
  const offered = useMemo(() => {
    const suggested = stage?.suggestedComponents;
    if (showAllComponents || !suggested?.length) return components;
    const keep = new Set([...suggested, ...(stage?.componentId ? [stage.componentId] : [])]);
    const subset = components.filter((c) => keep.has(c.id));
    return subset.length ? subset : components;
  }, [components, stage?.suggestedComponents, stage?.componentId, showAllComponents]);

  const componentsByKind = useMemo(() => {
    const groups = new Map<string, ComponentSpecLite[]>();
    for (const c of offered) {
      const list = groups.get(c.kind) ?? [];
      list.push(c);
      groups.set(c.kind, list);
    }
    return [...groups.entries()];
  }, [offered]);

  if (!stage) return null;

  const kind = KIND_META[stage.kind];
  const status = stageStatusMeta(stage);
  const phase =
    phases.find((p) => p.key === stage.phase) ?? CUSTOM_PHASE;
  const prev = index > 0 ? stages[index - 1] : null;
  const next = index < stages.length - 1 ? stages[index + 1] : null;

  return (
    <div className="animate-drawer-in overflow-hidden rounded-2xl border border-line bg-white">
      <div className="bg-gradient-to-r from-forest to-[#1F5A43] px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-extrabold tracking-[0.14em] text-sprout">
            CLOSER LOOK · PHASE {index + 1} · {phase.title.toUpperCase()}
          </span>
          <button
            onClick={() => onRemove(stage.id)}
            className="text-[10px] text-white/50 hover:text-red-300 hover:underline"
          >
            remove
          </button>
        </div>
        <input
          value={stage.label}
          onChange={(e) => onPatch(stage.id, { label: e.target.value })}
          className="mt-1 w-full rounded-lg border border-transparent bg-transparent px-1 py-0.5 font-display text-lg text-white outline-none transition focus:border-white/30 focus:bg-white/10"
        />
        <div className="mt-1.5 flex items-center gap-2">
          <span
            title={kind.hint}
            className="rounded-full bg-white/15 px-2 py-0.5 text-[10px] font-bold text-[#A8D08D]"
          >
            {kind.badge}
            {stage.kind === "lab" && stage.labTab ? ` · ${labTabLabel(stage.labTab)}` : ""}
          </span>
          <span className={`rounded-full bg-white px-2 py-0.5 text-[10px] font-bold ${status.className}`}>
            {status.label}
          </span>
        </div>
      </div>

      <div className="p-4 pt-3">
      <label className="block text-xs text-muted">What happens here</label>
      <textarea
        value={stage.description}
        onChange={(e) => onPatch(stage.id, { description: e.target.value })}
        rows={3}
        className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-xs"
      />

      {stage.kind === "lab" && stage.labTab && (
        <button
          onClick={() => onOpenLab?.(stage.labTab!)}
          disabled={!onOpenLab}
          className="mt-3 w-full rounded-full bg-[#2563EB] py-2 text-xs font-bold text-white shadow-[0_2px_10px_rgba(37,99,235,0.35)] transition hover:-translate-y-px hover:opacity-90 disabled:opacity-50"
        >
          Open in {labTabLabel(stage.labTab)} →
        </button>
      )}

      {stage.kind === "agent" && (
        <p className="mt-3 rounded-lg bg-[#F3EEFB] p-2 text-xs text-[#6D28D9]">
          🤖 A supervised run dispatches the DeepAgent here: it works the objective above with
          search + analysis tools, and its findings land Evidence-locked with a full step trace.
        </p>
      )}

      {stage.kind !== "component" && stage.kind !== "agent" && (
        <label className="mt-3 flex items-center gap-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={stage.markedDone}
            onChange={(e) => onPatch(stage.id, { markedDone: e.target.checked })}
            className="h-3.5 w-3.5 accent-leaf"
          />
          Mark stage complete
        </label>
      )}

      {stage.kind === "component" && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <label className="block text-xs text-muted">
              Component{!showAllComponents && stage.suggestedComponents?.length
                ? " · suggested for this phase" : ""}
            </label>
            {!!stage.suggestedComponents?.length && (
              <button
                onClick={() => setShowAllComponents((v) => !v)}
                className="text-[10px] text-[#2563EB] hover:underline"
              >
                {showAllComponents ? "show suggested only" : "show all components"}
              </button>
            )}
          </div>
          {components.length === 0 ? (
            <p className="text-xs text-muted">No components loaded — is the API running?</p>
          ) : (
            <select
              value={stage.componentId ?? ""}
              onChange={(e) => onPatch(stage.id, { componentId: e.target.value })}
              className="w-full rounded-lg border border-line px-2 py-1.5 text-sm"
            >
              {componentsByKind.map(([groupKind, list]) => (
                <optgroup key={groupKind} label={groupKind}>
                  {list.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          )}

          <label className="block text-xs text-muted">Params (JSON)</label>
          <textarea
            defaultValue={JSON.stringify(stage.params ?? {}, null, 0)}
            onBlur={(e) => {
              try {
                onPatch(stage.id, { params: JSON.parse(e.target.value || "{}") });
                setParamsError(null);
              } catch {
                setParamsError("Invalid JSON — not saved.");
              }
            }}
            rows={3}
            className={`w-full rounded-lg border px-2 py-1.5 font-mono text-xs ${
              paramsError ? "border-red-400" : "border-line"
            }`}
          />
          {paramsError && <p className="text-xs text-red-600">{paramsError}</p>}

          {stage.result && (
            <div className="rounded-lg bg-bg p-2">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    stage.status === "succeeded"
                      ? "bg-leaf/20 text-forest"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {stage.status}
                  {stage.result.evidence_count != null
                    ? ` · 🔒 ${stage.result.evidence_count} evidence`
                    : ""}
                </span>
                {stage.result.run_id && <ProvenanceBadge runId={stage.result.run_id} />}
              </div>
              {stage.result.error && (
                <p className="mt-1 text-xs text-red-600">{stage.result.error}</p>
              )}
              {stage.result.preview != null && (
                <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-ink">
                  {JSON.stringify(stage.result.preview, null, 1).slice(0, 1000)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-line pt-2 text-xs">
        {prev ? (
          <button onClick={() => onSelect(prev.id)} className="text-muted hover:text-forest">
            ← {index} · {prev.label}
          </button>
        ) : (
          <span />
        )}
        {next ? (
          <button onClick={() => onSelect(next.id)} className="text-muted hover:text-forest">
            {index + 2} · {next.label} →
          </button>
        ) : (
          <span />
        )}
      </div>
      </div>
    </div>
  );
}
