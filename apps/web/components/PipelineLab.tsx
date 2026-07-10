"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Papa from "papaparse";
import { Api, demoApi, type ComponentSpecLite, type PipelineResult } from "@/lib/api";
import {
  FLOW_TEMPLATES,
  type FlowNodeKind,
  type FlowStage,
} from "@/lib/pipelineTemplates";
import FileDropzone from "@/components/FileDropzone";
import ProvenanceBadge from "@/components/ProvenanceBadge";

const GRID_COLS = 4;
const NODE_W = 200;
const CELL_W = 240;
const CELL_H = 110;

type StepStatus = "idle" | "running" | "succeeded" | "failed" | "guided";

type StageState = FlowStage & {
  status: StepStatus;
  result?: { run_id?: string; evidence_count?: number; error?: string; preview?: unknown };
};

const KIND_HINT: Record<FlowNodeKind, string> = {
  component: "Runnable — executes as an Evidence-locked run",
  lab: "Lab stage — do this work in its Lab tab",
  manual: "Manual stage — human work outside the platform",
};

function nodeStyle(stage: StageState, selected: boolean): React.CSSProperties {
  const base: React.CSSProperties = {
    width: NODE_W, fontSize: 12, padding: 10, borderRadius: 14,
    border: `2px ${stage.kind === "manual" ? "dashed" : "solid"} ${selected ? "#6DB33F" : "#E4EBE1"}`,
    background: "#fff", color: "#14342A",
  };
  if (stage.kind === "lab") base.background = "#EDF4FB";
  if (stage.kind === "manual") base.background = "#F6F7F5";
  if (stage.status === "running") { base.background = "#FEF3C7"; base.border = "2px solid #F59E0B"; }
  if (stage.status === "succeeded") { base.background = "#6DB33F"; base.color = "#fff"; }
  if (stage.status === "failed") { base.background = "#C0392B"; base.color = "#fff"; }
  if (stage.status === "guided") base.border = `2px ${stage.kind === "manual" ? "dashed" : "solid"} #93B8DF`;
  return base;
}

export default function PipelineLab({ projectId }: { projectId: string }) {
  const [components, setComponents] = useState<ComponentSpecLite[]>([]);
  const [stages, setStages] = useState<StageState[]>([]);
  const [flowName, setFlowName] = useState<string>("Blank canvas");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Api.listComponents().then((r) => setComponents(r.components)).catch(() => setComponents([]));
  }, []);

  const loadTemplate = useCallback((key: string) => {
    const template = FLOW_TEMPLATES.find((t) => t.key === key);
    if (!template) return;
    setFlowName(template.name);
    setStages(template.stages.map((s) => ({ ...s, status: "idle" as StepStatus })));
    setSelectedId(null);
    setError(null);
  }, []);

  function loadCsv(files: File[]) {
    Papa.parse<Record<string, unknown>>(files[0], {
      header: true, dynamicTyping: true, skipEmptyLines: true,
      complete: (res) => { setRows(res.data); setFileName(files[0].name); },
    });
  }

  function addStage(kind: FlowNodeKind) {
    const id = `n${Date.now()}`;
    const stage: StageState = kind === "component"
      ? { id, kind, label: components[0]?.name ?? "Component", description: "Runnable step.",
          componentId: components[0]?.id, params: {}, status: "idle" }
      : { id, kind, label: kind === "lab" ? "Lab stage" : "Manual stage",
          description: "Describe this stage.", status: "idle" };
    setStages((s) => [...s, stage]);
    setSelectedId(id);
  }

  function updateStage(id: string, patch: Partial<StageState>) {
    setStages((all) => all.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }

  function removeStage(id: string) {
    setStages((all) => all.filter((s) => s.id !== id));
    if (selectedId === id) setSelectedId(null);
  }

  async function runFlow() {
    const runnable = stages.filter((s) => s.kind === "component" && s.componentId);
    if (runnable.length === 0) {
      setError("No runnable component stages in this flow.");
      return;
    }
    setBusy(true);
    setError(null);
    setStages((all) =>
      all.map((s) =>
        s.kind === "component" ? { ...s, status: "running", result: undefined }
          : { ...s, status: "guided" },
      ),
    );
    try {
      const result: PipelineResult = await Api.runPipeline(projectId, {
        steps: runnable.map((s) => ({ component_id: s.componentId!, params: s.params ?? {} })),
        dataset: rows.length ? rows : null,
      });
      setStages((all) => {
        let i = 0;
        return all.map((s) => {
          if (s.kind !== "component" || !s.componentId) return s;
          const step = result.steps[i++];
          return {
            ...s,
            status: (step?.status === "succeeded" ? "succeeded" : "failed") as StepStatus,
            result: step,
          };
        });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "pipeline run failed");
      setStages((all) =>
        all.map((s) => (s.status === "running" ? { ...s, status: "failed" } : s)),
      );
    } finally {
      setBusy(false);
    }
  }

  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = stages.map((s, i) => ({
      id: s.id,
      position: { x: (i % GRID_COLS) * CELL_W, y: Math.floor(i / GRID_COLS) * CELL_H },
      data: {
        label: `${s.kind === "component" ? "⚙️" : s.kind === "lab" ? "🧪" : "👤"} ${s.label}${
          s.status === "guided" ? (s.kind === "lab" ? " · open its Lab" : " · human step") : ""
        }`,
      },
      style: nodeStyle(s, s.id === selectedId),
    }));
    const edges: Edge[] = stages.slice(1).map((s, i) => ({
      id: `e${i}`, source: stages[i].id, target: s.id, animated: true,
      style: { stroke: "#A8D08D" },
    }));
    return { nodes, edges };
  }, [stages, selectedId]);

  const selected = stages.find((s) => s.id === selectedId) ?? null;
  const runnableCount = stages.filter((s) => s.kind === "component").length;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-display text-xl text-forest">Pipeline · {flowName}</h2>
            <p className="mt-1 text-sm text-muted">
              n8n-style flow: ⚙️ components run autonomously (Evidence-locked); 🧪 Lab stages are
              human-in-the-loop — Run highlights them and each opens in its Lab tab; 👤 manual
              stages are offline human work. Load a pre-configured firm flow or build your own.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {FLOW_TEMPLATES.map((t) => (
              <button
                key={t.key}
                onClick={() => loadTemplate(t.key)}
                title={t.tagline}
                className="rounded-full border border-leaf px-3 py-1.5 text-sm text-forest hover:bg-leaf/10"
              >
                {t.name}
              </button>
            ))}
            <button
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  const seed = await demoApi.seed(projectId);
                  setRows(seed.rows);
                  setFileName(`demo · ${seed.scenario}`);
                  loadTemplate("ngo-policy");
                  setError(null);
                } catch (e) {
                  setError(e instanceof Error ? `seed failed: ${e.message}` : "seed failed");
                } finally {
                  setBusy(false);
                }
              }}
              disabled={busy}
              title="Seed a realistic NGO education scenario (dataset + evidence + survey + personas) and load the flow"
              className="rounded-full bg-forest px-3 py-1.5 text-sm text-white hover:bg-forest/90 disabled:opacity-50"
            >
              🌱 Load demo scenario
            </button>
            <button
              onClick={() => { setStages([]); setFlowName("Blank canvas"); setSelectedId(null); }}
              className="rounded-full border border-line px-3 py-1.5 text-sm text-ink/60 hover:bg-bg"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <button onClick={() => addStage("component")}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg">
            + ⚙️ Component
          </button>
          <button onClick={() => addStage("lab")}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg">
            + 🧪 Lab stage
          </button>
          <button onClick={() => addStage("manual")}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg">
            + 👤 Manual stage
          </button>
          <span className="mx-2 h-5 w-px bg-line" />
          <button onClick={runFlow} disabled={busy || runnableCount === 0}
            className="rounded-lg bg-leaf px-4 py-1.5 font-medium text-white hover:opacity-90 disabled:opacity-50">
            {busy ? "Running…" : `▶ Run ${runnableCount} runnable step${runnableCount === 1 ? "" : "s"}`}
          </button>
        </div>
        <div className="mt-3">
          <FileDropzone multiple={false} accept=".csv"
            hint={rows.length ? `${fileName} · ${rows.length} rows` : "Drop a starting CSV for the runnable steps (optional)"}
            onFiles={loadCsv} />
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {stages.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
          <div className="h-[420px] overflow-hidden rounded-2xl border border-line bg-white">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodeClick={(_, node) => setSelectedId(node.id)}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#E4EBE1" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>

          <div className="rounded-2xl border border-line bg-white p-4">
            {!selected ? (
              <p className="text-sm text-ink/50">Click a node to configure it.</p>
            ) : (
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-bg px-2 py-0.5 text-xs text-ink/60">
                    {KIND_HINT[selected.kind]}
                  </span>
                  <button onClick={() => removeStage(selected.id)} className="text-xs text-red-600 hover:underline">
                    remove
                  </button>
                </div>
                <input
                  value={selected.label}
                  onChange={(e) => updateStage(selected.id, { label: e.target.value })}
                  className="w-full rounded-lg border border-line px-2 py-1.5 font-medium text-forest"
                />
                <textarea
                  value={selected.description}
                  onChange={(e) => updateStage(selected.id, { description: e.target.value })}
                  rows={3}
                  className="w-full rounded-lg border border-line px-2 py-1.5 text-xs"
                />
                {selected.kind === "component" && (
                  <>
                    <label className="block text-xs text-ink/50">Component</label>
                    <select
                      value={selected.componentId ?? ""}
                      onChange={(e) => updateStage(selected.id, { componentId: e.target.value })}
                      className="w-full rounded-lg border border-line px-2 py-1.5"
                    >
                      {components.map((c) => (
                        <option key={c.id} value={c.id}>{c.kind} · {c.name}</option>
                      ))}
                    </select>
                    <label className="block text-xs text-ink/50">Params (JSON)</label>
                    <textarea
                      defaultValue={JSON.stringify(selected.params ?? {}, null, 0)}
                      onBlur={(e) => {
                        try {
                          updateStage(selected.id, { params: JSON.parse(e.target.value || "{}") });
                          setError(null);
                        } catch {
                          setError(`Invalid JSON params on “${selected.label}” — not saved.`);
                        }
                      }}
                      rows={3}
                      className="w-full rounded-lg border border-line px-2 py-1.5 font-mono text-xs"
                    />
                    {selected.result && (
                      <div className="rounded-lg bg-bg p-2">
                        <div className="flex items-center gap-2">
                          <span className={`rounded-full px-2 py-0.5 text-xs ${
                            selected.status === "succeeded"
                              ? "bg-leaf/20 text-forest" : "bg-red-100 text-red-700"
                          }`}>
                            {selected.status}
                            {selected.result.evidence_count != null
                              ? ` · ${selected.result.evidence_count} evidence` : ""}
                          </span>
                          {selected.result.run_id && <ProvenanceBadge runId={selected.result.run_id} />}
                        </div>
                        {selected.result.error && (
                          <p className="mt-1 text-xs text-red-600">{selected.result.error}</p>
                        )}
                        {selected.result.preview != null && (
                          <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-ink">
                            {JSON.stringify(selected.result.preview, null, 1).slice(0, 1000)}
                          </pre>
                        )}
                      </div>
                    )}
                  </>
                )}
                {selected.kind === "lab" && selected.labTab && (
                  <p className="rounded-lg bg-[#EDF4FB] p-2 text-xs text-ink/70">
                    Do this stage in the <span className="font-medium">{selected.labTab}</span> tab
                    above, then come back and continue the flow.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
