"use client";

import LabChat from "@/components/LabChat";
import { useCallback, useEffect, useState } from "react";
import {
  Api,
  ApiError,
  surveysApi,
  type DirectorFinding,
  type FieldQuestion,
  type QuestionType,
  type QuotaCell,
  type Survey,
  type SurveyMonitor,
  type SurveyResponseRow,
  type SurveyStructure,
  type TwinDryRunReport,
} from "@/lib/api";

const QUESTION_TYPES: QuestionType[] = ["single", "multi", "scale", "open_text", "number"];

function emptyStructure(): SurveyStructure {
  return { sections: [{ id: "s1", title: "Section 1", questions: [] }], logic: [] };
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="font-display text-lg text-forest">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export default function FieldLab({ projectId }: { projectId: string }) {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setSurveys(await surveysApi.list(projectId));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (selected) {
    return (
      <SurveyDetail
        surveyId={selected}
        onBack={() => {
          setSelected(null);
          void refresh();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <LabChat projectId={projectId} lab="field" />
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink/70">
          Design a survey, publish a public link, and watch responses land in real time.
        </p>
        <CreateButton projectId={projectId} onCreated={(id) => setSelected(id)} />
      </div>
      {loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : surveys.length === 0 ? (
        <Card title="No surveys yet">
          <p className="text-sm text-ink/60">Create your first survey to start fielding.</p>
        </Card>
      ) : (
        <div className="grid gap-3">
          {surveys.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelected(s.id)}
              className="flex items-center justify-between rounded-2xl border border-line bg-white p-4 text-left hover:border-leaf"
            >
              <div>
                <div className="font-medium text-forest">{s.title || "Untitled survey"}</div>
                <div className="text-xs text-ink/50">
                  {s.structure?.sections?.reduce((n, sec) => n + sec.questions.length, 0) ?? 0}{" "}
                  questions
                </div>
              </div>
              <StatusChip status={s.status} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const color: Record<string, string> = {
    draft: "bg-bg text-ink/60 border-line",
    live: "bg-leaf/15 text-forest border-leaf",
    paused: "bg-amber-100 text-amber-800 border-amber-300",
    closed: "bg-ink/10 text-ink/60 border-line",
  };
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs ${color[status] ?? color.draft}`}>
      {status}
    </span>
  );
}

function CreateButton({
  projectId,
  onCreated,
}: {
  projectId: string;
  onCreated: (id: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function create() {
    setBusy(true);
    try {
      const s = await surveysApi.create(projectId, "Untitled survey", emptyStructure());
      onCreated(s.id);
    } finally {
      setBusy(false);
    }
  }
  return (
    <button
      onClick={create}
      disabled={busy}
      className="rounded-full bg-leaf px-4 py-1.5 text-sm font-medium text-white hover:bg-leaf/90 disabled:opacity-50"
    >
      {busy ? "Creating…" : "+ New survey"}
    </button>
  );
}

// ----------------------------- detail (builder + dashboard) -----------------------------

function SurveyDetail({ surveyId, onBack }: { surveyId: string; onBack: () => void }) {
  const [survey, setSurvey] = useState<Survey | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setSurvey(await surveysApi.get(surveyId));
  }, [surveyId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!survey) return <p className="text-sm text-ink/50">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-sm text-forest hover:underline">
          ← All surveys
        </button>
        <StatusChip status={survey.status} />
      </div>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}
      {survey.status === "draft" ? (
        <Builder survey={survey} onChange={setSurvey} onError={setErr} reload={load} />
      ) : (
        <Dashboard survey={survey} reload={load} />
      )}
    </div>
  );
}

function Builder({
  survey,
  onChange,
  onError,
  reload,
}: {
  survey: Survey;
  onChange: (s: Survey) => void;
  onError: (e: string | null) => void;
  reload: () => Promise<void>;
}) {
  const [structure, setStructure] = useState<SurveyStructure>(survey.structure);
  const [title, setTitle] = useState(survey.title);
  const [quotas, setQuotas] = useState<QuotaCell[]>(survey.quotas ?? []);
  const [hypotheses, setHypotheses] = useState(survey.prereg?.hypotheses ?? "");
  const [analyses, setAnalyses] = useState((survey.prereg?.planned_analyses ?? []).join("\n"));
  const [saving, setSaving] = useState(false);

  const plannedAnalyses = () => analyses.split("\n").map((a) => a.trim()).filter(Boolean);

  const allQuestions = structure.sections.flatMap((s) => s.questions);

  function updateQuestion(sIdx: number, qIdx: number, patch: Partial<FieldQuestion>) {
    const next = structuredClone(structure);
    next.sections[sIdx].questions[qIdx] = {
      ...next.sections[sIdx].questions[qIdx],
      ...patch,
    };
    setStructure(next);
  }

  function addQuestion(sIdx: number) {
    const next = structuredClone(structure);
    const n = allQuestions.length + 1;
    next.sections[sIdx].questions.push({
      id: `q${n}`,
      type: "single",
      text: "New question",
      required: true,
      options: ["Option A", "Option B"],
    });
    setStructure(next);
  }

  function removeQuestion(sIdx: number, qIdx: number) {
    const next = structuredClone(structure);
    next.sections[sIdx].questions.splice(qIdx, 1);
    setStructure(next);
  }

  function addSection() {
    const next = structuredClone(structure);
    next.sections.push({
      id: `s${next.sections.length + 1}`,
      title: `Section ${next.sections.length + 1}`,
      questions: [],
    });
    setStructure(next);
  }

  async function save() {
    setSaving(true);
    onError(null);
    try {
      await surveysApi.patch(survey.id, { title, structure });
      await surveysApi.setQuotas(survey.id, quotas);
      await surveysApi.setPrereg(survey.id, hypotheses, plannedAnalyses());
      await reload();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "save failed");
    } finally {
      setSaving(false);
    }
  }

  async function publish() {
    setSaving(true);
    onError(null);
    try {
      await surveysApi.patch(survey.id, { title, structure });
      await surveysApi.setQuotas(survey.id, quotas);
      await surveysApi.setPrereg(survey.id, hypotheses, plannedAnalyses());
      await surveysApi.publish(survey.id);
      await reload();  // reload() refreshes the survey to the live state → renders the dashboard
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "publish failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Survey">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-lg border border-line px-3 py-2 text-sm"
          placeholder="Survey title"
        />
      </Card>

      {structure.sections.map((section, sIdx) => (
        <Card key={section.id} title={section.title}>
          <div className="space-y-3">
            {section.questions.map((q, qIdx) => (
              <div key={q.id} className="rounded-xl border border-line p-3">
                <div className="flex gap-2">
                  <input
                    value={q.text}
                    onChange={(e) => updateQuestion(sIdx, qIdx, { text: e.target.value })}
                    className="flex-1 rounded-lg border border-line px-2 py-1.5 text-sm"
                  />
                  <select
                    value={q.type}
                    onChange={(e) =>
                      updateQuestion(sIdx, qIdx, { type: e.target.value as QuestionType })
                    }
                    className="rounded-lg border border-line px-2 py-1.5 text-sm"
                  >
                    {QUESTION_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => removeQuestion(sIdx, qIdx)}
                    className="rounded-lg border border-line px-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    ✕
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-ink/60">
                  <label className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={q.required ?? false}
                      onChange={(e) => updateQuestion(sIdx, qIdx, { required: e.target.checked })}
                    />
                    required
                  </label>
                  <span className="text-ink/40">id: {q.id}</span>
                </div>
                {(q.type === "single" || q.type === "multi") && (
                  <input
                    value={(q.options ?? []).join(", ")}
                    onChange={(e) =>
                      updateQuestion(sIdx, qIdx, {
                        options: e.target.value.split(",").map((o) => o.trim()).filter(Boolean),
                      })
                    }
                    className="mt-2 w-full rounded-lg border border-line px-2 py-1.5 text-sm"
                    placeholder="Comma-separated options"
                  />
                )}
                {q.type === "scale" && (
                  <div className="mt-2 flex gap-2 text-sm">
                    <input
                      type="number"
                      value={q.scale?.min ?? 1}
                      onChange={(e) =>
                        updateQuestion(sIdx, qIdx, {
                          scale: { min: Number(e.target.value), max: q.scale?.max ?? 5 },
                        })
                      }
                      className="w-20 rounded-lg border border-line px-2 py-1.5"
                    />
                    <span className="self-center text-ink/50">to</span>
                    <input
                      type="number"
                      value={q.scale?.max ?? 5}
                      onChange={(e) =>
                        updateQuestion(sIdx, qIdx, {
                          scale: { min: q.scale?.min ?? 1, max: Number(e.target.value) },
                        })
                      }
                      className="w-20 rounded-lg border border-line px-2 py-1.5"
                    />
                  </div>
                )}
              </div>
            ))}
            <button
              onClick={() => addQuestion(sIdx)}
              className="rounded-lg border border-dashed border-leaf px-3 py-1.5 text-sm text-forest hover:bg-leaf/5"
            >
              + Add question
            </button>
          </div>
        </Card>
      ))}

      <button onClick={addSection} className="text-sm text-forest hover:underline">
        + Add section
      </button>

      <LogicEditor
        structure={structure}
        questions={allQuestions}
        onChange={setStructure}
      />
      <QuotaEditor quotas={quotas} questions={allQuestions} onChange={setQuotas} />

      <Card title="Pre-registration (locks at publish)">
        <p className="mb-2 text-xs text-ink/50">
          Freeze your hypotheses and planned analyses before fielding. Once published these can&apos;t
          change — later analyses are labelled pre-registered vs exploratory.
        </p>
        <label className="text-xs text-ink/60">Hypotheses</label>
        <textarea
          value={hypotheses}
          onChange={(e) => setHypotheses(e.target.value)}
          rows={2}
          className="mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm"
          placeholder="e.g. Perceived safety, not price, is the primary adoption barrier."
        />
        <label className="mt-3 block text-xs text-ink/60">Planned analyses (one per line)</label>
        <textarea
          value={analyses}
          onChange={(e) => setAnalyses(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm"
          placeholder={"crosstab intent by gender\ndriver analysis of switch intent"}
        />
      </Card>

      <TwinDryRunPanel survey={survey} onError={onError} />

      <div className="flex gap-2">
        <button
          onClick={save}
          disabled={saving}
          className="rounded-full border border-line px-4 py-1.5 text-sm text-forest hover:bg-bg disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save draft"}
        </button>
        <button
          onClick={publish}
          disabled={saving}
          className="rounded-full bg-leaf px-4 py-1.5 text-sm font-medium text-white hover:bg-leaf/90 disabled:opacity-50"
        >
          Publish
        </button>
      </div>
    </div>
  );
}

function TwinDryRunPanel({
  survey,
  onError,
}: {
  survey: Survey;
  onError: (e: string | null) => void;
}) {
  const [n, setN] = useState(20);
  const [report, setReport] = useState<TwinDryRunReport | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    onError(null);
    try {
      // runs against the last saved draft — save first to include unsaved edits
      setReport(await surveysApi.twinDryRun(survey.id, n, {}));
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "dry-run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Synthetic twin dry-run">
      <p className="mb-2 text-xs text-ink/50">
        Simulate respondents taking this survey before you spend on fielding — surfaces drop-off,
        confusing questions, and expected answer spread. Synthetic: for design only, never evidence.
      </p>
      <div className="flex items-center gap-2">
        <label className="text-sm text-ink/60">Personas</label>
        <input
          type="number"
          value={n}
          min={1}
          max={100}
          onChange={(e) => setN(Number(e.target.value))}
          className="w-20 rounded-lg border border-line px-2 py-1 text-sm"
        />
        <button
          onClick={run}
          disabled={busy}
          className="rounded-full border border-line px-4 py-1.5 text-sm text-forest hover:bg-bg disabled:opacity-50"
        >
          {busy ? "Simulating…" : "Run dry-run"}
        </button>
      </div>
      {report && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {report.caveat}
          </div>
          <div>
            Predicted completion:{" "}
            <span className="font-medium text-forest">
              {Math.round(report.completion_rate * 100)}%
            </span>{" "}
            <span className="text-ink/50">({report.completed}/{report.personas_run})</span>
          </div>
          {report.predicted_dropoff.length > 0 && (
            <div>
              <div className="text-xs text-ink/50">Predicted drop-off</div>
              <ul className="list-inside list-disc">
                {report.predicted_dropoff.map((d) => (
                  <li key={d.qid}>
                    {d.qid}: {d.dropped} would abandon here
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.confusing_items.length > 0 && (
            <div>
              <div className="text-xs text-ink/50">Confusing questions</div>
              <ul className="list-inside list-disc">
                {report.confusing_items.map((c) => (
                  <li key={c.qid}>
                    {c.qid} ({c.count}){c.notes[0] ? ` — “${c.notes[0]}”` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function LogicEditor({
  structure,
  questions,
  onChange,
}: {
  structure: SurveyStructure;
  questions: FieldQuestion[];
  onChange: (s: SurveyStructure) => void;
}) {
  function update(logic: SurveyStructure["logic"]) {
    onChange({ ...structure, logic });
  }
  function addRule() {
    if (questions.length === 0) return;
    update([
      ...structure.logic,
      {
        if: { qid: questions[0].id, op: "eq", value: "" },
        then: { action: "screen_out" },
      },
    ]);
  }
  return (
    <Card title="Skip logic">
      <div className="space-y-2">
        {structure.logic.map((rule, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-ink/50">if</span>
            <select
              value={rule.if.qid}
              onChange={(e) => {
                const l = structuredClone(structure.logic);
                l[i].if.qid = e.target.value;
                update(l);
              }}
              className="rounded-lg border border-line px-2 py-1"
            >
              {questions.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.id}
                </option>
              ))}
            </select>
            <select
              value={rule.if.op}
              onChange={(e) => {
                const l = structuredClone(structure.logic);
                l[i].if.op = e.target.value as LogicRuleOp;
                update(l);
              }}
              className="rounded-lg border border-line px-2 py-1"
            >
              {(["eq", "ne", "gt", "lt", "in"] as const).map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
            <input
              value={String(rule.if.value ?? "")}
              onChange={(e) => {
                const l = structuredClone(structure.logic);
                l[i].if.value = e.target.value;
                update(l);
              }}
              className="w-24 rounded-lg border border-line px-2 py-1"
              placeholder="value"
            />
            <span className="text-ink/50">then</span>
            <select
              value={rule.then.action}
              onChange={(e) => {
                const l = structuredClone(structure.logic);
                l[i].then.action = e.target.value as "skip_to" | "screen_out";
                update(l);
              }}
              className="rounded-lg border border-line px-2 py-1"
            >
              <option value="screen_out">screen out</option>
              <option value="skip_to">skip to</option>
            </select>
            {rule.then.action === "skip_to" && (
              <select
                value={rule.then.target ?? ""}
                onChange={(e) => {
                  const l = structuredClone(structure.logic);
                  l[i].then.target = e.target.value;
                  update(l);
                }}
                className="rounded-lg border border-line px-2 py-1"
              >
                <option value="">—</option>
                {questions.map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.id}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={() => update(structure.logic.filter((_, j) => j !== i))}
              className="text-red-600"
            >
              ✕
            </button>
          </div>
        ))}
        <button onClick={addRule} className="text-sm text-forest hover:underline">
          + Add rule
        </button>
      </div>
    </Card>
  );
}

type LogicRuleOp = "eq" | "ne" | "gt" | "lt" | "in";

function QuotaEditor({
  quotas,
  questions,
  onChange,
}: {
  quotas: QuotaCell[];
  questions: FieldQuestion[];
  onChange: (q: QuotaCell[]) => void;
}) {
  function addQuota() {
    if (questions.length === 0) return;
    onChange([
      ...quotas,
      { name: `Cell ${quotas.length + 1}`, conditions: [{ qid: questions[0].id, value: "" }], target: 100 },
    ]);
  }
  return (
    <Card title="Quotas">
      <div className="space-y-2">
        {quotas.map((quota, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2 text-sm">
            <input
              value={quota.name}
              onChange={(e) => {
                const q = structuredClone(quotas);
                q[i].name = e.target.value;
                onChange(q);
              }}
              className="w-28 rounded-lg border border-line px-2 py-1"
            />
            <span className="text-ink/50">when</span>
            <select
              value={quota.conditions[0]?.qid ?? ""}
              onChange={(e) => {
                const q = structuredClone(quotas);
                q[i].conditions = [{ qid: e.target.value, value: q[i].conditions[0]?.value ?? "" }];
                onChange(q);
              }}
              className="rounded-lg border border-line px-2 py-1"
            >
              {questions.map((qq) => (
                <option key={qq.id} value={qq.id}>
                  {qq.id}
                </option>
              ))}
            </select>
            <span className="text-ink/50">=</span>
            <input
              value={String(quota.conditions[0]?.value ?? "")}
              onChange={(e) => {
                const q = structuredClone(quotas);
                q[i].conditions = [{ qid: q[i].conditions[0]?.qid ?? "", value: e.target.value }];
                onChange(q);
              }}
              className="w-24 rounded-lg border border-line px-2 py-1"
            />
            <span className="text-ink/50">target</span>
            <input
              type="number"
              value={quota.target}
              onChange={(e) => {
                const q = structuredClone(quotas);
                q[i].target = Number(e.target.value);
                onChange(q);
              }}
              className="w-20 rounded-lg border border-line px-2 py-1"
            />
            <button onClick={() => onChange(quotas.filter((_, j) => j !== i))} className="text-red-600">
              ✕
            </button>
          </div>
        ))}
        <button onClick={addQuota} className="text-sm text-forest hover:underline">
          + Add quota cell
        </button>
      </div>
    </Card>
  );
}

// ----------------------------- live dashboard -----------------------------

function Dashboard({ survey, reload }: { survey: Survey; reload: () => Promise<void> }) {
  const [monitor, setMonitor] = useState<SurveyMonitor | null>(null);
  const [responses, setResponses] = useState<SurveyResponseRow[]>([]);
  const [findings, setFindings] = useState<DirectorFinding[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const publicUrl = survey.public_token
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/s/${survey.public_token}`
    : "";

  const poll = useCallback(async () => {
    setMonitor(await surveysApi.monitor(survey.id));
    setResponses(await surveysApi.responses(survey.id));
    setFindings((await surveysApi.director(survey.id)).findings);
  }, [survey.id]);

  useEffect(() => {
    void poll();
    const t = setInterval(() => {
      if (document.visibilityState === "visible") void poll();
    }, 10000);
    return () => clearInterval(t);
  }, [poll]);

  async function act(fn: () => Promise<unknown>, label: string) {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      await reload();
      setMsg(label);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Public link">
        {publicUrl ? (
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded-lg bg-bg px-3 py-2 text-sm">{publicUrl}</code>
            <button
              onClick={() => navigator.clipboard.writeText(publicUrl)}
              className="rounded-lg border border-line px-3 py-2 text-sm text-forest hover:bg-bg"
            >
              Copy
            </button>
            <a
              href={publicUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-line px-3 py-2 text-sm text-forest hover:bg-bg"
            >
              Open
            </a>
          </div>
        ) : (
          <p className="text-sm text-ink/50">No public token.</p>
        )}
      </Card>

      {survey.prereg?.frozen_at && (
        <Card title="🔒 Pre-registered">
          <p className="text-xs text-ink/50">
            Locked {new Date(survey.prereg.frozen_at).toLocaleString()}
          </p>
          {survey.prereg.hypotheses && (
            <p className="mt-2 text-sm text-forest">{survey.prereg.hypotheses}</p>
          )}
          {(survey.prereg.planned_analyses ?? []).length > 0 && (
            <ul className="mt-2 list-inside list-disc text-sm text-ink/70">
              {survey.prereg.planned_analyses!.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {findings.length > 0 && (
        <Card title="🧭 Field Director">
          <div className="space-y-2">
            {findings.map((f, i) => (
              <div
                key={i}
                className={`rounded-xl border p-3 ${
                  f.severity === "high"
                    ? "border-red-200 bg-red-50"
                    : "border-amber-200 bg-amber-50"
                }`}
              >
                <div className="text-sm font-medium text-ink">{f.message}</div>
                <div className="mt-1 text-xs text-ink/60">Proposed: {f.proposal}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {monitor && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label="Completes" value={monitor.completes} tone="leaf" />
          <Stat label="In progress" value={monitor.in_progress} />
          <Stat label="Screened out" value={monitor.screened_out} />
          <Stat label="Quota full" value={monitor.quota_full} />
          <Stat label="Flagged" value={monitor.flagged} tone="amber" />
        </div>
      )}

      {monitor && monitor.quotas.length > 0 && (
        <Card title="Quota fill">
          <div className="space-y-2">
            {monitor.quotas.map((q) => (
              <div key={q.name}>
                <div className="flex justify-between text-xs text-ink/60">
                  <span>{q.name}</span>
                  <span>
                    {q.current} / {q.target}
                  </span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-bg">
                  <div
                    className="h-2 rounded-full bg-leaf"
                    style={{ width: `${Math.min(100, (q.current / Math.max(1, q.target)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {monitor && (
        <Card title="Drop-off by question">
          <div className="space-y-1">
            {monitor.dropoff.map((d) => (
              <div key={d.qid} className="flex items-center gap-2 text-xs">
                <span className="w-14 text-ink/50">{d.qid}</span>
                <div className="h-3 flex-1 rounded bg-bg">
                  <div
                    className="h-3 rounded bg-forest/70"
                    style={{ width: `${Math.min(100, (d.answered / Math.max(1, d.reached)) * 100)}%` }}
                  />
                </div>
                <span className="w-24 text-right text-ink/50">
                  {d.answered}/{d.reached} answered
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {survey.status === "live" && (
          <button
            onClick={() => act(() => surveysApi.pause(survey.id), "Paused")}
            disabled={busy}
            className="rounded-full border border-line px-4 py-1.5 text-sm text-forest hover:bg-bg"
          >
            Pause
          </button>
        )}
        {survey.status === "paused" && (
          <button
            onClick={() => act(() => surveysApi.publish(survey.id), "Resumed")}
            disabled={busy}
            className="rounded-full bg-leaf px-4 py-1.5 text-sm text-white hover:bg-leaf/90"
          >
            Resume
          </button>
        )}
        {survey.status !== "closed" && (
          <button
            onClick={() => act(() => surveysApi.close(survey.id), "Closed")}
            disabled={busy}
            className="rounded-full border border-line px-4 py-1.5 text-sm text-red-600 hover:bg-red-50"
          >
            Close
          </button>
        )}
        <button
          onClick={() =>
            act(async () => {
              const r = await surveysApi.exportDataset(survey.id);
              setMsg(`Exported dataset (${r.n_rows} rows)`);
            }, "")
          }
          disabled={busy}
          className="rounded-full border border-line px-4 py-1.5 text-sm text-forest hover:bg-bg"
        >
          Export as Dataset
        </button>
        {msg && <span className="text-sm text-leaf">{msg}</span>}
      </div>

      <AnalyzePanel survey={survey} responses={responses} />

      <Card title={`Responses (${responses.length})`}>
        <div className="max-h-72 overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-ink/50">
              <tr>
                <th className="py-1">Status</th>
                <th>Flags</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {responses.map((r) => (
                <tr key={r.id} className="border-t border-line/60">
                  <td className="py-1">{r.status}</td>
                  <td className="text-amber-700">{r.flags.join(", ")}</td>
                  <td className="text-ink/50">
                    {r.duration_seconds != null ? `${Math.round(r.duration_seconds)}s` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

type CrosstabTable = {
  columns: { category: string; letter: string; base: number }[];
  rows: { stub_value: string; cells: Record<string, { pct: number; n: number; sig_higher_than: string }> }[];
  chi_square: number | null;
  p_value: number | null;
  total_n: number;
};

function AnalyzePanel({ survey, responses }: { survey: Survey; responses: SurveyResponseRow[] }) {
  const questions = survey.structure.sections.flatMap((s) => s.questions);
  const categorical = questions.filter((q) => q.type === "single");
  const numeric = questions.filter((q) => q.type === "scale" || q.type === "number");
  const [banner, setBanner] = useState(categorical[0]?.id ?? "");
  const [stub, setStub] = useState(categorical[1]?.id ?? categorical[0]?.id ?? "");
  const [metricCol, setMetricCol] = useState(numeric[0]?.id ?? "");
  const [metric, setMetric] = useState<"mean" | "top2box" | "nps">("mean");
  const [table, setTable] = useState<CrosstabTable | null>(null);
  const [metricOut, setMetricOut] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const records = responses
    .filter((r) => r.status === "complete" || r.status === "flagged")
    .map((r) => r.answers);

  async function runCrosstab() {
    setBusy(true);
    setErr(null);
    try {
      const res = await Api.runComponent(survey.project_id, "analyzer.crosstab",
        { banner, stub }, records);
      setTable(res.preview as unknown as CrosstabTable);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "crosstab failed");
    } finally {
      setBusy(false);
    }
  }

  async function runMetric() {
    setBusy(true);
    setErr(null);
    try {
      const q = numeric.find((x) => x.id === metricCol);
      const res = await Api.runComponent(survey.project_id, "analyzer.survey_metrics",
        { column: metricCol, metric, scale_max: q?.scale?.max ?? 5 }, records);
      setMetricOut(res.preview);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "metric failed");
    } finally {
      setBusy(false);
    }
  }

  if (records.length === 0) return null;

  return (
    <Card title="Analyze (Evidence-locked)">
      {err && <p className="mb-2 rounded-lg bg-red-50 px-3 py-1.5 text-xs text-red-700">{err}</p>}
      {categorical.length >= 1 && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-ink/50">Crosstab</span>
          <select value={stub} onChange={(e) => setStub(e.target.value)}
            className="rounded-lg border border-line px-2 py-1">
            {categorical.map((q) => <option key={q.id} value={q.id}>{q.id}</option>)}
          </select>
          <span className="text-ink/50">by</span>
          <select value={banner} onChange={(e) => setBanner(e.target.value)}
            className="rounded-lg border border-line px-2 py-1">
            {categorical.map((q) => <option key={q.id} value={q.id}>{q.id}</option>)}
          </select>
          <button onClick={runCrosstab} disabled={busy || !banner || !stub}
            className="rounded-full border border-line px-3 py-1 text-forest hover:bg-bg disabled:opacity-50">
            Run
          </button>
        </div>
      )}
      {table && (
        <div className="mt-3 overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-ink/50">
              <tr>
                <th className="py-1 pr-3">{stub} ↓</th>
                {table.columns.map((c) => (
                  <th key={c.category} className="pr-3">
                    {c.category} <span className="text-leaf">({c.letter})</span>
                    <div className="font-normal text-ink/40">n={c.base}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((r) => (
                <tr key={r.stub_value} className="border-t border-line/60">
                  <td className="py-1 pr-3 font-medium text-forest">{r.stub_value}</td>
                  {table.columns.map((c) => {
                    const cell = r.cells[c.category];
                    return (
                      <td key={c.category} className="pr-3">
                        {cell.pct}%
                        {cell.sig_higher_than && (
                          <sup className="ml-0.5 font-semibold text-leaf">{cell.sig_higher_than}</sup>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-[10px] text-ink/40">
            Superscript letter = significantly higher than that column (95%).
            {table.chi_square != null && ` χ²=${table.chi_square}, p=${table.p_value}.`} n={table.total_n}.
          </p>
        </div>
      )}
      {numeric.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line/60 pt-3 text-sm">
          <span className="text-ink/50">Metric</span>
          <select value={metric} onChange={(e) => setMetric(e.target.value as typeof metric)}
            className="rounded-lg border border-line px-2 py-1">
            <option value="mean">mean ± CI</option>
            <option value="top2box">top-2-box</option>
            <option value="nps">NPS</option>
          </select>
          <span className="text-ink/50">of</span>
          <select value={metricCol} onChange={(e) => setMetricCol(e.target.value)}
            className="rounded-lg border border-line px-2 py-1">
            {numeric.map((q) => <option key={q.id} value={q.id}>{q.id}</option>)}
          </select>
          <button onClick={runMetric} disabled={busy || !metricCol}
            className="rounded-full border border-line px-3 py-1 text-forest hover:bg-bg disabled:opacity-50">
            Run
          </button>
          {metricOut && (
            <span className="rounded-lg bg-bg px-3 py-1 font-mono text-xs text-forest">
              {JSON.stringify(metricOut).slice(0, 160)}
            </span>
          )}
        </div>
      )}
    </Card>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "leaf" | "amber" }) {
  const color = tone === "leaf" ? "text-forest" : tone === "amber" ? "text-amber-700" : "text-ink";
  return (
    <div className="rounded-2xl border border-line bg-white p-4 text-center">
      <div className={`font-display text-2xl ${color}`}>{value}</div>
      <div className="text-xs text-ink/50">{label}</div>
    </div>
  );
}
