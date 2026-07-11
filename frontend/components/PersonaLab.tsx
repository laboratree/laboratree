"use client";

import LabChat from "@/components/LabChat";
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  personasApi,
  surveysApi,
  type PersonaCohort,
  type PersonaRow,
  type Survey,
  type TwinDryRunReport,
} from "@/lib/api";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="font-display text-lg text-forest">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export default function PersonaLab({ projectId }: { projectId: string }) {
  const [cohorts, setCohorts] = useState<PersonaCohort[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [name, setName] = useState("Cohort A");
  const [n, setN] = useState(20);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setCohorts(await personasApi.cohorts(projectId));
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function create() {
    setBusy(true);
    setErr(null);
    try {
      const c = await personasApi.createCohort(projectId, name, n, {});
      setSelected(c.id);
      await refresh();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "create failed");
    } finally {
      setBusy(false);
    }
  }

  if (selected) {
    return <CohortDetail cohortId={selected} projectId={projectId} onBack={() => { setSelected(null); void refresh(); }} />;
  }

  return (
    <div className="space-y-4">
      <LabChat projectId={projectId} lab="personas" />
      <p className="text-sm text-ink/70">
        Persistent synthetic respondents with stable personalities and memory — the same cohort can
        be re-surveyed across waves and stays consistent. Synthetic: for design, never real evidence.
      </p>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}

      <Card title="Build a cohort">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-line px-3 py-1.5" placeholder="Cohort name" />
          <label className="text-ink/60">Personas</label>
          <input type="number" value={n} min={1} max={100} onChange={(e) => setN(Number(e.target.value))}
            className="w-20 rounded-lg border border-line px-2 py-1.5" />
          <button onClick={create} disabled={busy}
            className="rounded-full bg-leaf px-4 py-1.5 font-medium text-white hover:bg-leaf/90 disabled:opacity-50">
            {busy ? "Building…" : "Build cohort"}
          </button>
        </div>
      </Card>

      {cohorts.length > 0 && (
        <div className="grid gap-2">
          {cohorts.map((c) => (
            <button key={c.id} onClick={() => setSelected(c.id)}
              className="flex items-center justify-between rounded-2xl border border-line bg-white p-4 text-left hover:border-leaf">
              <span className="font-medium text-forest">{c.name}</span>
              <span className="text-xs text-ink/50">
                {c.n} personas · {c.waves} wave{c.waves === 1 ? "" : "s"}
                {c.conditioning === "objective" && (
                  <span title={`Objective-conditioned — mean trait bias: ${JSON.stringify(c.trait_delta ?? {})}. Not valid for RCT/impact estimation.`}
                    className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                    ⚠ objective-conditioned
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CohortDetail({ cohortId, projectId, onBack }: { cohortId: string; projectId: string; onBack: () => void }) {
  const [personas, setPersonas] = useState<PersonaRow[]>([]);
  const [edgeCount, setEdgeCount] = useState(0);
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [surveyId, setSurveyId] = useState("");
  const [report, setReport] = useState<(TwinDryRunReport & { wave: number }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setPersonas(await personasApi.personas(cohortId));
    setEdgeCount((await personasApi.graph(cohortId)).edges.length);
    const s = await surveysApi.list(projectId);
    setSurveys(s);
    if (s.length && !surveyId) setSurveyId(s[0].id);
  }, [cohortId, projectId, surveyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runWave() {
    setBusy(true);
    setErr(null);
    try {
      setReport(await personasApi.runWave(cohortId, surveyId));
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "wave run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="text-sm text-forest hover:underline">← All cohorts</button>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}

      <Card title="Run a survey wave">
        {surveys.length === 0 ? (
          <p className="text-sm text-ink/50">Create a survey in the Field Lab first.</p>
        ) : (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <select value={surveyId} onChange={(e) => setSurveyId(e.target.value)}
              className="rounded-lg border border-line px-2 py-1.5">
              {surveys.map((s) => <option key={s.id} value={s.id}>{s.title || "Untitled"}</option>)}
            </select>
            <button onClick={runWave} disabled={busy || !surveyId}
              className="rounded-full bg-leaf px-4 py-1.5 text-white hover:bg-leaf/90 disabled:opacity-50">
              {busy ? "Simulating…" : "Run wave"}
            </button>
          </div>
        )}
        {report && (
          <div className="mt-3 space-y-1 text-sm">
            <div className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-800">{report.caveat}</div>
            <div>Wave {report.wave} · completion {Math.round(report.completion_rate * 100)}%</div>
            {report.predicted_dropoff.length > 0 && (
              <div className="text-xs text-ink/60">
                Drop-off: {report.predicted_dropoff.map((d) => `${d.qid} (${d.dropped})`).join(", ")}
              </div>
            )}
          </div>
        )}
      </Card>

      <Card title={`Personas (${personas.length})`}>
        <p className="mb-2 text-xs text-ink/50">
          🕸 Social network: {edgeCount} connections (homophily — similar personas link up). Neighbours&apos;
          prior-wave answers influence each persona, so opinions diffuse across waves.
        </p>
        <div className="max-h-96 space-y-2 overflow-auto">
          {personas.map((p) => (
            <div key={p.id} className="rounded-xl border border-line p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-forest">{p.handle}</span>
                <span className="text-xs text-ink/50">{p.memory_waves} wave{p.memory_waves === 1 ? "" : "s"} in memory</span>
              </div>
              <p className="mt-1 text-xs text-ink/60">{p.bio}</p>
              <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-ink/40">
                {Object.entries(p.traits).map(([t, v]) => (
                  <span key={t}>{t.slice(0, 4)} {Math.round(v * 100)}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
