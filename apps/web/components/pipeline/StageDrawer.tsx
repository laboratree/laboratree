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

  const index = stages.findIndex((s) => s.id === selectedId);
  const stage = index >= 0 ? stages[index] : null;

  const componentsByKind = useMemo(() => {
    const groups = new Map<string, ComponentSpecLite[]>();
    for (const c of components) {
      const list = groups.get(c.kind) ?? [];
      list.push(c);
      groups.set(c.kind, list);
    }
    return [...groups.entries()];
  }, [components]);

  if (!stage) return null;

  const kind = KIND_META[stage.kind];
  const status = stageStatusMeta(stage);
  const phase =
    phases.find((p) => p.key === stage.phase) ?? CUSTOM_PHASE;
  const prev = index > 0 ? stages[index - 1] : null;
  const next = index < stages.length - 1 ? stages[index + 1] : null;

  return (
    <div className="animate-drawer-in rounded-2xl border border-line border-l-4 border-l-leaf bg-white p-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-wider text-muted">
          CLOSER LOOK · PHASE {index + 1} · {phase.title.toUpperCase()}
        </span>
        <button
          onClick={() => onRemove(stage.id)}
          className="text-xs text-red-600 hover:underline"
        >
          remove
        </button>
      </div>

      <input
        value={stage.label}
        onChange={(e) => onPatch(stage.id, { label: e.target.value })}
        className="mt-2 w-full rounded-lg border border-line px-2 py-1.5 font-display text-base text-forest"
      />

      <div className="mt-2 flex items-center gap-2">
        <span
          title={kind.hint}
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${kind.badgeClass}`}
        >
          {kind.badge}
          {stage.kind === "lab" && stage.labTab ? ` · ${labTabLabel(stage.labTab)}` : ""}
        </span>
        <span className={`text-xs font-semibold ${status.className}`}>{status.label}</span>
      </div>

      <label className="mt-3 block text-xs text-muted">What happens here</label>
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
          className="mt-3 w-full rounded-lg bg-[#2563EB] py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          Open in {labTabLabel(stage.labTab)} →
        </button>
      )}

      {stage.kind !== "component" && (
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
          <label className="block text-xs text-muted">Component</label>
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
  );
}
