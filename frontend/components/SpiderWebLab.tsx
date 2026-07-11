"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { labAgentsApi, spiderApi, type AgentRunView, type SpiderMission } from "@/lib/api";

// SpiderWeb — the agentic web navigator. Dark web-canvas theme: the mission graph grows LIVE
// as pages are visited (nodes colored by yield), items stream into the table with provenance.

const POLL_MS = 2500;
const NEON = "#22D3EE";
const NEON_HIT = "#4ADE80";
const NEON_MISS = "#475569";

type PageStep = { url: string; matched?: boolean; skipped?: string; depth?: number };

function missionGraph(steps: PageStep[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = steps.map((s, i) => ({
    id: `p${i}`,
    position: { x: (i % 5) * 190, y: Math.floor(i / 5) * 90 },
    data: { label: s.url.replace(/^https?:\/\//, "").slice(0, 34) + (s.matched ? " ✦" : "") },
    style: {
      background: "#0B1220",
      color: s.skipped ? NEON_MISS : s.matched ? NEON_HIT : NEON,
      border: `1px solid ${s.matched ? NEON_HIT : "#1E293B"}`,
      borderRadius: 10, fontSize: 10, padding: 6, width: 170,
      boxShadow: s.matched ? `0 0 12px ${NEON_HIT}44` : "none",
    },
  }));
  const edges: Edge[] = steps.slice(1).map((_, i) => ({
    id: `e${i}`, source: `p${i}`, target: `p${i + 1}`, animated: true,
    style: { stroke: `${NEON}66`, strokeWidth: 1 },
  }));
  return { nodes, edges };
}

export default function SpiderWebLab({ projectId }: { projectId: string }) {
  const [missions, setMissions] = useState<SpiderMission[]>([]);
  const [active, setActive] = useState<AgentRunView | null>(null);
  const [objective, setObjective] = useState("");
  const [seeds, setSeeds] = useState("");
  const [fields, setFields] = useState("");
  const [maxPages, setMaxPages] = useState(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try { setMissions(await spiderApi.list(projectId)); } catch { /* transient */ }
  }, [projectId]);

  useEffect(() => { void refresh(); }, [refresh]);

  // poll the active mission while it runs
  useEffect(() => {
    if (!active || (active.status !== "running" && active.status !== "queued")) return;
    const t = setTimeout(async () => {
      try {
        setActive(await labAgentsApi.run(projectId, active.id));
        void refresh();
      } catch { /* transient */ }
    }, POLL_MS);
    return () => clearTimeout(t);
  }, [active, projectId, refresh]);

  async function launch() {
    setBusy(true);
    setError(null);
    try {
      const schema = Object.fromEntries(
        fields.split(",").map((f) => f.trim()).filter(Boolean).map((f) => [f, f]));
      const { agent_run_id } = await spiderApi.create(projectId, {
        objective,
        seed_urls: seeds.split(/[\s,]+/).filter(Boolean),
        target_schema: schema,
        max_pages: maxPages,
      });
      setActive(await labAgentsApi.run(projectId, agent_run_id));
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "mission failed to launch");
    } finally {
      setBusy(false);
    }
  }

  const pages: PageStep[] = useMemo(
    () => (active?.steps ?? []).filter((s) => s.kind === "page") as unknown as PageStep[],
    [active]);
  const graph = useMemo(() => missionGraph(pages), [pages]);
  const records = (active?.records ?? []) as Record<string, unknown>[];

  return (
    <div className="space-y-4">
      {/* mission composer — dark web-canvas theme */}
      <div className="overflow-hidden rounded-2xl border border-[#1E293B] bg-[#0B1220] p-5">
        <h2 className="font-display text-xl text-white">
          🕸️ SpiderWeb <span className="ml-2 text-sm text-[#22D3EE]">the agentic web navigator</span>
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          Delegate a dig: only the objective is required — with no seeds it finds starting
          points itself via web, research-paper and reddit search, then navigates (redirects,
          listings, detail pages), extracts matching items into a real Dataset with per-row
          provenance, honors robots.txt, and resumes if stopped.
        </p>
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          <input value={objective} onChange={(e) => setObjective(e.target.value)}
            placeholder='Objective — e.g. "find all data-analyst job posts with salary + location"'
            className="rounded-lg border border-[#1E293B] bg-[#0F1A2E] px-3 py-2 text-sm text-white placeholder:text-slate-500" />
          <input value={seeds} onChange={(e) => setSeeds(e.target.value)}
            placeholder="Seed URL(s) — optional; empty = the agent finds seeds via web/paper/reddit search"
            className="rounded-lg border border-[#1E293B] bg-[#0F1A2E] px-3 py-2 text-sm text-white placeholder:text-slate-500" />
          <input value={fields} onChange={(e) => setFields(e.target.value)}
            placeholder="Fields to extract — optional; empty = snapshot crawl"
            className="rounded-lg border border-[#1E293B] bg-[#0F1A2E] px-3 py-2 text-sm text-white placeholder:text-slate-500" />
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-400">max pages</label>
            <input type="number" value={maxPages} min={1} max={200}
              onChange={(e) => setMaxPages(Number(e.target.value) || 30)}
              className="w-24 rounded-lg border border-[#1E293B] bg-[#0F1A2E] px-3 py-2 text-sm text-white" />
            <button onClick={launch}
              disabled={busy || !objective.trim()}
              className="rounded-full bg-[#22D3EE] px-5 py-2 text-sm font-bold text-[#0B1220] shadow-[0_0_18px_rgba(34,211,238,0.45)] transition hover:-translate-y-px disabled:opacity-40">
              {busy ? "Launching…" : "🕷️ Launch mission"}
            </button>
          </div>
        </div>
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </div>

      {/* live mission board */}
      {active && (
        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="h-[420px] overflow-hidden rounded-2xl border border-[#1E293B] bg-[#0B1220]">
            <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView
              nodesDraggable={false} nodesConnectable={false}
              proOptions={{ hideAttribution: true }}>
              <Background color="#1E293B" gap={22} />
            </ReactFlow>
          </div>
          <div className="rounded-2xl border border-[#1E293B] bg-[#0B1220] p-4">
            <p className="text-xs font-bold tracking-wider text-[#22D3EE]">
              {active.status.toUpperCase()} · {pages.length} pages · {records.length} items
            </p>
            <p className="mt-1 text-xs text-slate-400">{active.summary || active.task}</p>
            <div className="mt-3 max-h-72 overflow-y-auto">
              {records.map((r, i) => (
                <div key={i} className="mb-2 rounded-lg border border-[#1E293B] bg-[#0F1A2E] p-2">
                  {Object.entries(r).filter(([k]) => k !== "source_url").map(([k, v]) => (
                    <p key={k} className="text-[11px] text-slate-200">
                      <span className="text-slate-500">{k}:</span> {String(v ?? "—")}
                    </p>
                  ))}
                  <a href={String(r.source_url ?? "#")} target="_blank" rel="noreferrer"
                    className="text-[10px] text-[#22D3EE] hover:underline">
                    {String(r.source_url ?? "")}
                  </a>
                </div>
              ))}
              {records.length === 0 && (
                <p className="text-xs text-slate-500">no items collected yet…</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* mission history */}
      <div className="rounded-2xl border border-line bg-white p-4">
        <h3 className="font-display text-lg text-forest">Missions</h3>
        {missions.length === 0 ? (
          <p className="mt-2 text-sm text-ink/50">No missions yet — launch your first dig.</p>
        ) : (
          <div className="mt-2 space-y-1">
            {missions.map((m) => (
              <div key={m.id} className="flex items-center justify-between rounded-lg border border-line px-3 py-2">
                <button onClick={async () => setActive(await labAgentsApi.run(projectId, m.id))}
                  className="text-left text-sm text-forest hover:underline">
                  {m.objective}
                </button>
                <span className="text-xs text-ink/50">
                  {m.status} · {m.pages}p · {m.items} items
                  {m.status !== "succeeded" && (
                    <button onClick={async () => {
                      await spiderApi.resume(projectId, m.id);
                      setActive(await labAgentsApi.run(projectId, m.id));
                    }} className="ml-2 text-[#2563EB] hover:underline">resume</button>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
