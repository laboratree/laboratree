"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type NodeTypes } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Papa from "papaparse";
import {
  Api, demoApi, flowsApi,
  type ComponentSpecLite, type PipelineResult, type SuperviseReport,
} from "@/lib/api";
import { FLOW_TEMPLATES, type FlowNodeKind, type FlowPhase } from "@/lib/pipelineTemplates";
import type { LabTabKey } from "@/lib/labTabs";
import FileDropzone from "@/components/FileDropzone";
import { buildFlowGraph } from "./layout";
import { LaneNode } from "./LaneNode";
import { StageNode } from "./StageNode";
import StageDrawer from "./StageDrawer";
import { isRunDriven, isStageComplete, KIND_META, type StageState, type StepStatus } from "./types";

// Registered once at module scope — React Flow requires a stable nodeTypes reference.
const nodeTypes: NodeTypes = { stage: StageNode, lane: LaneNode };

export type PipelineLabProps = {
  projectId: string;
  onOpenLab?: (tab: LabTabKey) => void;
};

export default function PipelineLab({ projectId, onOpenLab }: PipelineLabProps) {
  const [components, setComponents] = useState<ComponentSpecLite[]>([]);
  const [stages, setStages] = useState<StageState[]>([]);
  const [phases, setPhases] = useState<FlowPhase[]>([]);
  const [flowName, setFlowName] = useState("Blank canvas");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seedNote, setSeedNote] = useState<string | null>(null);
  const [pendingGate, setPendingGate] = useState<
    { threadId: string; stageId: string; summary: string } | null>(null);

  useEffect(() => {
    Api.listComponents().then((r) => setComponents(r.components)).catch(() => setComponents([]));
  }, []);

  const loadTemplate = useCallback((key: string) => {
    const template = FLOW_TEMPLATES.find((t) => t.key === key);
    if (!template) return;
    setFlowName(template.name);
    setPhases(template.phases);
    setStages(
      template.stages.map((s) => ({ ...s, status: "idle" as StepStatus, markedDone: false })),
    );
    setSelectedId(null);
    setError(null);
    setSeedNote(null);
  }, []);

  function loadCsv(files: File[]) {
    Papa.parse<Record<string, unknown>>(files[0], {
      header: true, dynamicTyping: true, skipEmptyLines: true,
      complete: (res) => { setRows(res.data); setFileName(files[0].name); },
    });
  }

  function addStage(kind: FlowNodeKind) {
    if (busy) return; // a run in flight maps results onto the current stages — freeze the flow
    const id = `n${Date.now()}`;
    const base = { id, phase: "custom", status: "idle" as StepStatus, markedDone: false };
    const stage: StageState = kind === "component"
      ? { ...base, kind, label: components[0]?.name ?? "Component",
          description: "Runnable step.", componentId: components[0]?.id, params: {} }
      : kind === "agent"
        ? { ...base, kind, label: "Agent stage",
            description: "Describe the objective — the DeepAgent works it with tools on a supervised run." }
        : { ...base, kind, label: kind === "lab" ? "Lab stage" : "Manual stage",
            description: "Describe this stage." };
    setStages((s) => [...s, stage]);
    setSelectedId(id);
  }

  function updateStage(id: string, patch: Partial<StageState>) {
    setStages((all) => all.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }

  function removeStage(id: string) {
    if (busy) return; // a run in flight maps results onto the current stages — freeze the flow
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
    // A run only touches component stages — lab/manual completion belongs to the user.
    setStages((all) =>
      all.map((s) =>
        s.kind === "component"
          ? { ...s, status: "running" as StepStatus, result: undefined }
          : s,
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
        all.map((s) => (s.status === "running" ? { ...s, status: "failed" as StepStatus } : s)),
      );
    } finally {
      setBusy(false);
    }
  }

  async function seedDemo() {
    setBusy(true);
    setError(null);
    try {
      const seed = await demoApi.seed(projectId);
      setRows(seed.rows);
      setFileName(`demo · ${seed.scenario}`);
      const template = FLOW_TEMPLATES.find((t) => t.key === "policy-research");
      if (template) {
        setFlowName(template.name);
        setPhases(template.phases);
        // The seed genuinely activated the lab stages (published survey, persona wave,
        // hypothesis runs, shared report) — reflect that as completed with the artifact note.
        // Run-driven stages the seeder executed surface as succeeded runs with provenance,
        // not as idle cards that would silently re-run on ▶.
        setStages(template.stages.map((s) => {
          const artifact = seed.stages?.[s.id];
          const runId = typeof artifact?.run_id === "string" ? artifact.run_id : undefined;
          const description = runId
            ? `${s.description} (demo: Evidence-locked run recorded)`
            : s.description;
          if (runId && isRunDriven(s.kind)) {
            return {
              ...s,
              status: "succeeded" as StepStatus,
              markedDone: false,
              result: {
                component_id: s.componentId ?? s.id,
                status: "succeeded",
                run_id: runId,
                evidence_count:
                  typeof artifact?.evidence === "number" ? artifact.evidence : undefined,
              },
              description,
            };
          }
          return {
            ...s,
            status: "idle" as StepStatus,
            markedDone: s.kind === "lab" && !!artifact,
            description,
          };
        }));
        setSelectedId(null);
      }
      const field = seed.stages?.field as { completes?: number } | undefined;
      setSeedNote(
        `Seeded: survey LIVE with ${field?.completes ?? 0} labeled completes, persona wave 1 run, `
        + `${seed.evidence_total} Evidence records, report shared.`,
      );
    } catch (e) {
      setError(e instanceof Error ? `seed failed: ${e.message}` : "seed failed");
    } finally {
      setBusy(false);
    }
  }

  const flowKey = FLOW_TEMPLATES.find((t) => t.name === flowName)?.key;

  const applySuperviseReport = useCallback((report: SuperviseReport) => {
    const byId = new Map(report.stages.map((r) => [r.id, r]));
    const runDriven = isRunDriven;
    setStages((all) => all.map((s) => {
      const r = byId.get(s.id);
      if (!r) return { ...s, status: "idle" as StepStatus };
      const succeeded = r.status === "succeeded";
      return {
        ...s,
        status: (runDriven(s.kind)
          ? (succeeded ? "succeeded" : r.status === "failed" ? "failed" : "idle")
          : "idle") as StepStatus,
        markedDone: !runDriven(s.kind) && succeeded,
        result: r.run_id
          ? { component_id: s.componentId ?? r.id, status: r.status,
              run_id: r.run_id, evidence_count: r.evidence,
              error: r.error ?? undefined, preview: r.artifacts }
          : undefined,
        description: r.summary ? `${s.description} — ⚡ ${r.summary}` : s.description,
      };
    }));
    setPendingGate(report.status === "paused" && report.pending_gate
      ? { threadId: report.thread_id, stageId: report.pending_gate.stage_id,
          summary: report.pending_gate.summary ?? "" }
      : null);
    const done = report.stages.filter((r) => r.status === "succeeded").length;
    setSeedNote(
      `Supervised run ${report.status}: ${done}/${report.stages.length} phases · `
      + `${report.evidence_total} Evidence · lab agents: ${report.labs.join(", ") || "—"}`
      + (report.status === "paused" ? " · waiting on your gate decision below." : ""),
    );
  }, []);

  async function runOrchestrated() {
    if (!flowKey) return;
    setBusy(true);
    setError(null);
    setSeedNote(null);
    setStages((all) => all.map((s) => ({ ...s, status: "running" as StepStatus })));
    try {
      // agent stages carry their objective in the description — the DeepAgent works from it
      const objectives = Object.fromEntries(
        stages.filter((s) => s.kind === "agent").map((s) => [s.id, s.description]));
      const report = await flowsApi.supervise(
        projectId, flowKey, stages.map((s) => s.id), objectives);
      applySuperviseReport(report);
    } catch (e) {
      setError(e instanceof Error ? `supervised run failed: ${e.message}` : "run failed");
      setStages((all) =>
        all.map((s) => (s.status === "running" ? { ...s, status: "idle" as StepStatus } : s)),
      );
    } finally {
      setBusy(false);
    }
  }

  async function resolveGate(approved: boolean) {
    if (!pendingGate) return;
    setBusy(true);
    setError(null);
    try {
      applySuperviseReport(await flowsApi.resume(pendingGate.threadId, approved));
    } catch (e) {
      setError(e instanceof Error ? `resume failed: ${e.message}` : "resume failed");
    } finally {
      setBusy(false);
    }
  }

  const graph = useMemo(
    () => buildFlowGraph({ stages, phases, selectedId, runInFlight: busy }),
    [stages, phases, selectedId, busy],
  );

  const runnableCount = stages.filter((s) => s.kind === "component").length;
  const completeCount = stages.filter(isStageComplete).length;
  const progressPct = stages.length
    ? Math.round((completeCount / stages.length) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-line bg-white">
        <div className="flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-forest to-[#1F5A43] px-5 py-4">
          <div className="min-w-[240px]">
            <h2 className="font-display text-xl text-white">
              {flowName}
              <span className="ml-2 text-sm text-[#A8D08D]">
                · {stages.length} phases · {runnableCount} runnable
              </span>
            </h2>
            <div className="mt-2 flex items-center gap-2">
              <div className="h-1.5 w-56 overflow-hidden rounded-full bg-white/20">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-leaf to-sprout transition-all duration-700"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-xs font-semibold text-[#A8D08D]">
                {completeCount} / {stages.length} complete
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={runFlow} disabled={busy || runnableCount === 0}
              className="rounded-full bg-leaf px-5 py-2 text-sm font-bold text-white shadow-[0_2px_12px_rgba(109,179,63,0.5)] transition hover:-translate-y-px hover:opacity-90 disabled:opacity-50 disabled:shadow-none">
              {busy ? "Running…" : `▶ Run ${runnableCount} step${runnableCount === 1 ? "" : "s"}`}
            </button>
            {!!flowKey && (
              <button onClick={runOrchestrated} disabled={busy || stages.length === 0}
                title="Supervised run: the Supervisor dispatches every phase to its Lab agent, spawns the DeepAgent for uncovered stages, and pauses at human gates — durable and resumable."
                className="rounded-full border border-[#A8D08D]/50 bg-white/10 px-5 py-2 text-sm font-bold text-white transition hover:bg-white/20 disabled:opacity-50">
                {busy ? "Supervising…" : "⚡ Supervise flow"}
              </button>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 px-5 pt-4 text-sm">
          {FLOW_TEMPLATES.map((t) => (
            <button
              key={t.key}
              onClick={() => loadTemplate(t.key)}
              disabled={busy}
              title={t.tagline}
              className={`rounded-full border px-3 py-1.5 text-sm transition disabled:opacity-50 ${
                t.name === flowName
                  ? "border-forest bg-forest text-white"
                  : "border-leaf text-forest hover:bg-leaf/10"
              }`}
            >
              {t.name}
            </button>
          ))}
          <button
            onClick={seedDemo}
            disabled={busy}
            title="Seed a realistic NGO education scenario (dataset + evidence + survey + personas) and load the flow"
            className="rounded-full bg-leaf/15 px-3 py-1.5 text-sm font-semibold text-forest hover:bg-leaf/25 disabled:opacity-50"
          >
            🌱 Load demo scenario
          </button>
          <button
            onClick={() => {
              setStages([]); setPhases([]); setFlowName("Blank canvas"); setSelectedId(null);
            }}
            disabled={busy}
            className="rounded-full border border-line px-3 py-1.5 text-sm text-ink/60 hover:bg-bg disabled:opacity-50"
          >
            Clear
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 px-5 py-3 text-sm">
          <button onClick={() => addStage("component")} disabled={busy}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg disabled:opacity-50">
            + ⚙️ Component
          </button>
          <button onClick={() => addStage("lab")} disabled={busy}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg disabled:opacity-50">
            + 🧪 Lab stage
          </button>
          <button onClick={() => addStage("agent")} disabled={busy}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg disabled:opacity-50">
            + 🤖 Agent stage
          </button>
          <button onClick={() => addStage("manual")} disabled={busy}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg disabled:opacity-50">
            + 👤 Manual stage
          </button>
          <span className="mx-2 h-5 w-px bg-line" />
          {(Object.keys(KIND_META) as (keyof typeof KIND_META)[]).map((k) => (
            <span
              key={k}
              title={KIND_META[k].hint}
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${KIND_META[k].badgeClass}`}
            >
              {KIND_META[k].badge}
            </span>
          ))}
        </div>

        <div className="px-5 pb-4">
          <FileDropzone multiple={false} accept=".csv"
            hint={rows.length ? `${fileName} · ${rows.length} rows` : "Drop a starting CSV for the runnable steps (optional)"}
            onFiles={loadCsv} />
          {seedNote && <p className="mt-2 text-sm text-forest">🌱 {seedNote}</p>}
          {pendingGate && (
            <div className="mt-2 flex flex-wrap items-center gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5">
              <span className="text-sm text-amber-900">
                ⏸ Gate open at <span className="font-bold">{pendingGate.stageId}</span>
                {pendingGate.summary ? ` — ${pendingGate.summary}` : ""}. The run is checkpointed
                and waiting on you.
              </span>
              <span className="flex gap-2">
                <button onClick={() => resolveGate(true)} disabled={busy}
                  className="rounded-full bg-leaf px-4 py-1 text-xs font-bold text-white hover:opacity-90 disabled:opacity-50">
                  ✓ Approve & continue
                </button>
                <button onClick={() => resolveGate(false)} disabled={busy}
                  className="rounded-full border border-red-300 px-4 py-1 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-50">
                  ✕ Reject
                </button>
              </span>
            </div>
          )}
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </div>
      </div>

      {stages.length === 0 && (
        <div className="flex h-[320px] flex-col items-center justify-center rounded-2xl border border-dashed border-leaf/40 bg-[#F7FAF5] text-center">
          <span className="text-4xl">🧭</span>
          <p className="mt-3 font-display text-lg text-forest">Choose a research flow above</p>
          <p className="mt-1 max-w-md text-sm text-muted">
            Load a pre-configured lifecycle — every phase becomes a card on the canvas, grouped
            into color-coded lanes, with a closer look and lab deep-links one click away.
          </p>
        </div>
      )}

      {stages.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="h-[680px] overflow-hidden rounded-2xl border border-line bg-[#F7FAF5]">
            <ReactFlow
              nodes={graph.nodes}
              edges={graph.edges}
              nodeTypes={nodeTypes}
              nodesDraggable={false}
              nodesConnectable={false}
              onNodeClick={(_, node) => {
                if (node.type === "stage") setSelectedId(node.id);
              }}
              onPaneClick={() => setSelectedId(null)}
              defaultViewport={{ x: 24, y: 20, zoom: 0.8 }}
              minZoom={0.35}
              maxZoom={1.6}
              panOnScroll
              zoomOnScroll={false}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#DCE7D6" gap={22} />
              <Controls showInteractive={false} />
              <MiniMap
                pannable
                zoomable
                className="!h-28 !w-40"
                nodeColor={(n) =>
                  n.type === "lane"
                    ? "#E7F0E3"
                    : ((n.data as { accent?: string }).accent ?? "#6DB33F")
                }
                maskColor="rgba(20, 52, 42, 0.08)"
              />
            </ReactFlow>
          </div>

          {selectedId ? (
            <StageDrawer
              key={selectedId}
              stages={stages}
              phases={phases}
              selectedId={selectedId}
              components={components}
              onPatch={updateStage}
              onRemove={removeStage}
              onSelect={setSelectedId}
              onOpenLab={onOpenLab}
            />
          ) : (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-white p-6 text-center">
              <span className="text-2xl">🔍</span>
              <p className="mt-2 text-sm font-semibold text-forest">Closer look</p>
              <p className="mt-1 text-xs text-muted">
                Click any phase card on the canvas — its story, controls, evidence, and lab
                deep-link appear here.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
