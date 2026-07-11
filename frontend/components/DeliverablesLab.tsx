"use client";

import LabChat from "@/components/LabChat";
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  deliverablesApi,
  type ReportEvidence,
  type Report,
  type ReportBlock,
} from "@/lib/api";

const EVIDENCE_TYPES = new Set(["stat", "table", "chart", "quote"]);

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="font-display text-lg text-forest">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export default function DeliverablesLab({ projectId }: { projectId: string }) {
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setReports(await deliverablesApi.list(projectId));
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (selected) {
    return <ReportEditor reportId={selected} projectId={projectId} onBack={() => { setSelected(null); void refresh(); }} />;
  }

  return (
    <div className="space-y-4">
      <LabChat projectId={projectId} lab="deliver" />
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink/70">
          Compose client-ready reports. Every number, table, or quote must bind to real Evidence —
          hand-typed figures are refused.
        </p>
        <button
          onClick={async () => setSelected((await deliverablesApi.create(projectId)).id)}
          className="rounded-full bg-leaf px-4 py-1.5 text-sm font-medium text-white hover:bg-leaf/90"
        >
          + New report
        </button>
      </div>
      {reports.length === 0 ? (
        <Card title="No reports yet">
          <p className="text-sm text-ink/60">Create a report to assemble your findings.</p>
        </Card>
      ) : (
        <div className="grid gap-2">
          {reports.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelected(r.id)}
              className="flex items-center justify-between rounded-2xl border border-line bg-white p-4 text-left hover:border-leaf"
            >
              <span className="font-medium text-forest">{r.title}</span>
              <span className="text-xs text-ink/50">
                {r.blocks.length} blocks{r.share_token ? " · shared" : ""}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ReportEditor({
  reportId,
  projectId,
  onBack,
}: {
  reportId: string;
  projectId: string;
  onBack: () => void;
}) {
  const [report, setReport] = useState<Report | null>(null);
  const [evidence, setEvidence] = useState<ReportEvidence[]>([]);
  const [title, setTitle] = useState("");
  const [blocks, setBlocks] = useState<ReportBlock[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const r = await deliverablesApi.get(reportId);
    setReport(r);
    setTitle(r.title);
    setBlocks(r.blocks);
    setEvidence(await deliverablesApi.evidence(projectId));
  }, [reportId, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  function addBlock(type: ReportBlock["type"]) {
    const b: ReportBlock =
      type === "heading" ? { type, text: "Section heading" }
      : type === "text" ? { type, text: "" }
      : type === "methodology" ? { type, text: "n = …, weighting = …, field dates = …" }
      : { type, evidence_id: evidence[0]?.id, caption: "" };
    setBlocks((bs) => [...bs, b]);
  }

  function update(i: number, patch: Partial<ReportBlock>) {
    setBlocks((bs) => bs.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  }

  async function save() {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      await deliverablesApi.save(reportId, { title, blocks });
      setMsg("Saved.");
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "save failed");
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const { path } = await deliverablesApi.share(reportId);
    const url = `${window.location.origin}${path}`;
    await navigator.clipboard.writeText(url).catch(() => {});
    setMsg(`Public link copied: ${url}`);
    await load();
  }

  if (!report) return <p className="text-sm text-ink/50">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-sm text-forest hover:underline">← All reports</button>
        <div className="flex gap-2">
          <a href={deliverablesApi.renderUrl(reportId)} target="_blank" rel="noreferrer"
            className="rounded-full border border-line px-4 py-1.5 text-sm text-forest hover:bg-bg">
            Preview
          </a>
          <button onClick={share}
            className="rounded-full border border-line px-4 py-1.5 text-sm text-forest hover:bg-bg">
            Share
          </button>
          <button onClick={save} disabled={busy}
            className="rounded-full bg-leaf px-4 py-1.5 text-sm text-white hover:bg-leaf/90 disabled:opacity-50">
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}
      {msg && <p className="rounded-lg bg-leaf/10 px-3 py-2 text-sm text-forest">{msg}</p>}

      <Card title="Report">
        <input value={title} onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-lg border border-line px-3 py-2 text-sm" placeholder="Report title" />
      </Card>

      <div className="space-y-2">
        {blocks.map((b, i) => (
          <div key={i} className="rounded-xl border border-line bg-white p-3">
            <div className="flex items-center justify-between text-xs text-ink/50">
              <span className="rounded-full bg-bg px-2 py-0.5">{b.type}</span>
              <button onClick={() => setBlocks(blocks.filter((_, j) => j !== i))}
                className="text-red-600 hover:underline">remove</button>
            </div>
            {(b.type === "heading" || b.type === "text" || b.type === "methodology") ? (
              <textarea value={b.text ?? ""} onChange={(e) => update(i, { text: e.target.value })}
                rows={b.type === "heading" ? 1 : 3}
                className="mt-2 w-full rounded-lg border border-line px-2 py-1.5 text-sm" />
            ) : (
              <div className="mt-2 space-y-2">
                <select value={b.evidence_id ?? ""} onChange={(e) => update(i, { evidence_id: e.target.value })}
                  className="w-full rounded-lg border border-line px-2 py-1.5 text-sm">
                  <option value="">— pick Evidence —</option>
                  {evidence.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.label} ({e.kind}) = {JSON.stringify(e.value).slice(0, 40)}
                    </option>
                  ))}
                </select>
                <input value={b.caption ?? ""} onChange={(e) => update(i, { caption: e.target.value })}
                  placeholder="Caption (optional)"
                  className="w-full rounded-lg border border-line px-2 py-1.5 text-sm" />
              </div>
            )}
          </div>
        ))}
      </div>

      <Card title="Add block">
        <div className="flex flex-wrap gap-2 text-sm">
          {(["heading", "text", "stat", "quote", "table", "chart", "methodology"] as const).map((t) => (
            <button key={t} onClick={() => addBlock(t)}
              disabled={EVIDENCE_TYPES.has(t) && evidence.length === 0}
              title={EVIDENCE_TYPES.has(t) && evidence.length === 0 ? "Run an analysis first to produce Evidence" : ""}
              className="rounded-full border border-line px-3 py-1 text-forest hover:bg-bg disabled:opacity-40">
              + {t}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-ink/40">
          {evidence.length} Evidence record{evidence.length === 1 ? "" : "s"} available in this project.
        </p>
      </Card>
    </div>
  );
}
