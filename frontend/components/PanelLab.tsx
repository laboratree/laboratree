"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  panelApi,
  surveysApi,
  type Respondent,
  type Survey,
} from "@/lib/api";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="font-display text-lg text-forest">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export default function PanelLab({ projectId }: { projectId: string }) {
  const [respondents, setRespondents] = useState<Respondent[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRespondents(await panelApi.list(query || undefined));
  }, [query]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink/70">
        Your respondent panel — the only place personal data lives. Survey answers stay
        pseudonymous; deleting a person here never deletes their (unlinkable) answers.
      </p>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}
      {msg && <p className="rounded-lg bg-leaf/10 px-3 py-2 text-sm text-forest">{msg}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <AddRespondent onDone={refresh} onError={setErr} />
        <ImportCsv onDone={(r) => { setMsg(`Imported ${r.imported}, skipped ${r.skipped}.`); void refresh(); }} onError={setErr} />
      </div>

      <Card title={`Respondents (${respondents.length})`}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search name or email…"
          className="mb-3 w-full rounded-lg border border-line px-3 py-2 text-sm"
        />
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink/50">
              <tr>
                <th className="py-1"></th>
                <th>Email</th>
                <th>Name</th>
                <th>Consent</th>
                <th>Attributes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {respondents.map((r) => (
                <RespondentRow
                  key={r.id}
                  r={r}
                  checked={selected.has(r.id)}
                  onToggle={() => toggle(r.id)}
                  onChanged={refresh}
                  onError={setErr}
                />
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <InviteComposer
        projectId={projectId}
        selected={[...selected]}
        respondents={respondents}
        onDone={(r) => setMsg(`Invitations: ${r.sent} sent, ${r.skipped} skipped, ${r.failed} failed.`)}
        onError={setErr}
      />
    </div>
  );
}

function RespondentRow({
  r,
  checked,
  onToggle,
  onChanged,
  onError,
}: {
  r: Respondent;
  checked: boolean;
  onToggle: () => void;
  onChanged: () => Promise<void>;
  onError: (e: string) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function consent() {
    setBusy(true);
    try {
      await panelApi.consent(r.id, "Standard survey participation consent v1");
      await onChanged();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "consent failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete ${r.email}? Their identity is erased permanently (GDPR).`)) return;
    setBusy(true);
    try {
      await panelApi.remove(r.id);
      await onChanged();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr className="border-t border-line/60">
      <td className="py-1.5 pr-2">
        <input type="checkbox" checked={checked} onChange={onToggle} />
      </td>
      <td className="pr-3">{r.email}</td>
      <td className="pr-3 text-ink/70">{r.full_name || "—"}</td>
      <td className="pr-3">
        {r.consented_at ? (
          <span className="rounded-full bg-leaf/15 px-2 py-0.5 text-xs text-forest">consented</span>
        ) : (
          <button
            onClick={consent}
            disabled={busy}
            className="rounded-full border border-line px-2 py-0.5 text-xs text-forest hover:bg-bg"
          >
            record consent
          </button>
        )}
      </td>
      <td className="pr-3 text-xs text-ink/50">
        {Object.entries(r.attributes ?? {}).map(([k, v]) => `${k}: ${v}`).join(" · ") || "—"}
      </td>
      <td className="text-right">
        <button onClick={remove} disabled={busy} className="text-xs text-red-600 hover:underline">
          delete
        </button>
      </td>
    </tr>
  );
}

function AddRespondent({
  onDone,
  onError,
}: {
  onDone: () => Promise<void>;
  onError: (e: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    if (!email) return;
    setBusy(true);
    try {
      await panelApi.create(email, name, {});
      setEmail("");
      setName("");
      await onDone();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "could not add respondent");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Add respondent">
      <div className="flex flex-wrap gap-2">
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email@example.com"
          className="flex-1 rounded-lg border border-line px-3 py-2 text-sm"
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Full name (optional)"
          className="flex-1 rounded-lg border border-line px-3 py-2 text-sm"
        />
        <button
          onClick={add}
          disabled={busy || !email}
          className="rounded-full bg-leaf px-4 py-1.5 text-sm text-white hover:bg-leaf/90 disabled:opacity-50"
        >
          Add
        </button>
      </div>
    </Card>
  );
}

function ImportCsv({
  onDone,
  onError,
}: {
  onDone: (r: { imported: number; skipped: number }) => void;
  onError: (e: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function upload(file: File) {
    setBusy(true);
    try {
      onDone(await panelApi.importCsv(file));
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "import failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <Card title="Import CSV">
      <p className="mb-2 text-xs text-ink/50">
        Needs an <code>email</code> column; other columns become attributes. Duplicates are skipped.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        disabled={busy}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void upload(f);
        }}
        className="text-sm"
      />
    </Card>
  );
}

function InviteComposer({
  projectId,
  selected,
  respondents,
  onDone,
  onError,
}: {
  projectId: string;
  selected: string[];
  respondents: Respondent[];
  onDone: (r: { sent: number; skipped: number; failed: number }) => void;
  onError: (e: string) => void;
}) {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [surveyId, setSurveyId] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    surveysApi
      .list(projectId)
      .then((all) => {
        const live = all.filter((s) => s.status === "live");
        setSurveys(live);
        if (live.length > 0) setSurveyId(live[0].id);
      })
      .catch(() => {});
  }, [projectId]);

  const eligible = selected.filter((id) => {
    const r = respondents.find((x) => x.id === id);
    return r && r.consented_at && !r.do_not_contact;
  });

  async function send() {
    if (!surveyId || selected.length === 0) return;
    setBusy(true);
    try {
      onDone(await panelApi.invite(surveyId, selected));
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "invitations failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Invite to survey">
      {surveys.length === 0 ? (
        <p className="text-sm text-ink/50">No live surveys — publish one in the Field Lab first.</p>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={surveyId}
            onChange={(e) => setSurveyId(e.target.value)}
            className="rounded-lg border border-line px-3 py-2 text-sm"
          >
            {surveys.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title || "Untitled survey"}
              </option>
            ))}
          </select>
          <span className="text-sm text-ink/60">
            {selected.length} selected · {eligible.length} consented
          </span>
          <button
            onClick={send}
            disabled={busy || selected.length === 0}
            className="rounded-full bg-leaf px-4 py-1.5 text-sm text-white hover:bg-leaf/90 disabled:opacity-50"
          >
            {busy ? "Sending…" : "Send invitations"}
          </button>
        </div>
      )}
      <p className="mt-2 text-xs text-ink/40">
        Only consented, contactable respondents receive an email; each gets a unique link that ties
        their completion back — pseudonymously — to this panel.
      </p>
    </Card>
  );
}
