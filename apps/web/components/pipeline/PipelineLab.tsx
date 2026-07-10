"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, ReactFlow, type NodeTypes } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Papa from "papaparse";
import { Api, demoApi, flowsApi, type ComponentSpecLite, type PipelineResult } from "@/lib/api";
import { FLOW_TEMPLATES, type FlowNodeKind, type FlowPhase } from "@/lib/pipelineTemplates";
import type { LabTabKey } from "@/lib/labTabs";
import FileDropzone from "@/components/FileDropzone";
import { buildFlowGraph } from "./layout";
import { LaneNode } from "./LaneNode";
import { StageNode } from "./StageNode";
import StageDrawer from "./StageDrawer";
import { isStageComplete, KIND_META, type StageState, type StepStatus } from "./types";

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
    const id = `n${Date.now()}`;
    const base = { id, phase: "custom", status: "idle" as StepStatus, markedDone: false };
    const stage: StageState = kind === "component"
      ? { ...base, kind, label: components[0]?.name ?? "Component",
          description: "Runnable step.", componentId: components[0]?.id, params: {} }
      : { ...base, kind, label: kind === "lab" ? "Lab stage" : "Manual stage",
          description: "Describe this stage." };
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
      const template = FLOW_TEMPLATES.find((t) => t.key === "ngo-policy");
      if (template) {
        setFlowName(template.name);
        setPhases(template.phases);
        // The seed genuinely activated the lab stages (published survey, persona wave,
        // hypothesis runs, shared report) — reflect that as completed with the artifact note.
        setStages(template.stages.map((s) => {
          const artifact = seed.stages?.[s.id];
          const activated = s.kind !== "component" && s.kind !== "manual" && !!artifact;
          return {
            ...s,
            status: "idle" as StepStatus,
            markedDone: activated,
            description: artifact && "run_id" in artifact && artifact.run_id
              ? `${s.description} (demo: Evidence-locked run recorded)`
              : s.description,
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

  async function runOrchestrated() {
    if (!flowKey) return;
    setBusy(true);
    setError(null);
    setSeedNote(null);
    setStages((all) => all.map((s) => ({ ...s, status: "running" as StepStatus })));
    try {
      const report = await flowsApi.run(projectId, flowKey, stages.map((s) => s.id));
      const byId = new Map(report.stages.map((r) => [r.id, r]));
      setStages((all) => all.map((s) => {
        const r = byId.get(s.id);
        if (!r) return { ...s, status: "idle" as StepStatus };
        const succeeded = r.status === "succeeded";
        return {
          ...s,
          status: (s.kind === "component"
            ? (succeeded ? "succeeded" : r.status === "failed" ? "failed" : "idle")
            : "idle") as StepStatus,
          markedDone: s.kind !== "component" && succeeded,
          result: r.run_id
            ? { component_id: s.componentId ?? r.id, status: r.status,
                run_id: r.run_id, evidence_count: r.evidence,
                error: r.error ?? undefined, preview: r.artifacts }
            : undefined,
          description: r.summary ? `${s.description} — 🤖 ${r.summary}` : s.description,
        };
      }));
      setSeedNote(
        `Orchestrated run ${report.status}: ${report.stages.filter((r) => r.status === "succeeded").length}`
        + `/${report.stages.length} phases, ${report.evidence_total} Evidence, `
        + `${report.gates_opened} gate${report.gates_opened === 1 ? "" : "s"} awaiting approval.`,
      );
    } catch (e) {
      setError(e instanceof Error ? `orchestrated run failed: ${e.message}` : "run failed");
      setStages((all) =>
        all.map((s) => (s.status === "running" ? { ...s, status: "idle" as StepStatus } : s)),
      );
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
      <div className="rounded-2xl border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-[240px]">
            <h2 className="font-display text-xl text-forest">
              {flowName}
              <span className="ml-2 text-sm text-muted">
                · {stages.length} phases · {runnableCount} runnable
              </span>
            </h2>
            <div className="mt-2 flex items-center gap-2">
              <div className="h-1.5 w-56 overflow-hidden rounded-full bg-[#EEF3EA]">
                <div
                  className="h-full rounded-full bg-leaf transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-xs text-muted">
                {completeCount} / {stages.length} complete
              </span>
            </div>
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
              onClick={seedDemo}
              disabled={busy}
              title="Seed a realistic NGO education scenario (dataset + evidence + survey + personas) and load the flow"
              className="rounded-full bg-forest px-3 py-1.5 text-sm text-white hover:bg-forest/90 disabled:opacity-50"
            >
              🌱 Load demo scenario
            </button>
            <button
              onClick={() => {
                setStages([]); setPhases([]); setFlowName("Blank canvas"); setSelectedId(null);
              }}
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
          {flowKey === "ngo-policy" && (
            <button onClick={runOrchestrated} disabled={busy || stages.length === 0}
              title="Every phase runs as a sub-agent: analyses execute, the survey publishes and fields, personas simulate, the report composes — human steps open gates."
              className="rounded-lg bg-forest px-4 py-1.5 font-medium text-white hover:opacity-90 disabled:opacity-50">
              {busy ? "Orchestrating…" : "🤖 Run whole flow"}
            </button>
          )}
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

        <div className="mt-3">
          <FileDropzone multiple={false} accept=".csv"
            hint={rows.length ? `${fileName} · ${rows.length} rows` : "Drop a starting CSV for the runnable steps (optional)"}
            onFiles={loadCsv} />
        </div>
        {seedNote && <p className="mt-2 text-sm text-forest">🌱 {seedNote}</p>}
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {stages.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="h-[560px] overflow-hidden rounded-2xl border border-line bg-white">
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
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#E4EBE1" />
              <Controls showInteractive={false} />
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
            <div className="rounded-2xl border border-line bg-white p-4">
              <p className="text-sm text-ink/50">
                Select a phase on the canvas for a closer look — its story, controls, and
                results appear here.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
