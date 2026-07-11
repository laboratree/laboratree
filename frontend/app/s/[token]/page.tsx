"use client";

import { Suspense, use, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ApiError,
  publicSurveyApi,
  type PublicSurvey,
  type FieldQuestion,
  type SurveyStructure,
} from "@/lib/api";
import { END, nextQuestionId, orderedQids, SCREENED_OUT } from "@/lib/surveyLogic";

type Phase = "loading" | "error" | "welcome" | "question" | "done";
type Ending = "accepted" | "screened_out" | "quota_full";

function storageKey(token: string) {
  return `lt_survey_${token}`;
}

export default function PublicSurveyPage({ params }: { params: Promise<{ token: string }> }) {
  return (
    <Suspense fallback={<Shell><p className="text-ink/50">Loading…</p></Shell>}>
      <SurveyRunner params={params} />
    </Suspense>
  );
}

function SurveyRunner({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const searchParams = useSearchParams();
  const invitationToken = searchParams.get("inv") ?? undefined;
  const [survey, setSurvey] = useState<PublicSurvey | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [resumeKey, setResumeKey] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [currentQid, setCurrentQid] = useState<string | null>(null);
  const [ending, setEnding] = useState<Ending>("accepted");
  const [resumed, setResumed] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    publicSurveyApi
      .get(token)
      .then((s) => {
        setSurvey(s);
        setPhase(s.survey_status === "live" ? "welcome" : "error");
        if (s.survey_status === "paused") setErrorMsg("This survey is paused. Please check back soon.");
        else if (s.survey_status !== "live") setErrorMsg("This survey is not currently open.");
      })
      .catch((e) => {
        setErrorMsg(e instanceof ApiError ? e.message : "This survey link is not valid.");
        setPhase("error");
      });
  }, [token]);

  const structure: SurveyStructure = survey?.structure ?? { sections: [], logic: [] };

  const scheduleSave = useCallback(
    (rk: string, next: Record<string, unknown>) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        void publicSurveyApi.save(token, rk, next).catch(() => {});
      }, 700);
    },
    [token],
  );

  async function start() {
    const saved = localStorage.getItem(storageKey(token));
    const priorKey = saved ? (JSON.parse(saved).resume_key as string) : undefined;
    const priorAnswers = saved ? (JSON.parse(saved).answers as Record<string, unknown>) : {};
    try {
      const { resume_key } = await publicSurveyApi.start(token, priorKey, invitationToken);
      setResumeKey(resume_key);
      setAnswers(priorAnswers);
      localStorage.setItem(
        storageKey(token),
        JSON.stringify({ resume_key, answers: priorAnswers }),
      );
      const firstQ =
        Object.keys(priorAnswers).length > 0
          ? firstUnansweredOrFirst(structure, priorAnswers)
          : nextQuestionId(structure, priorAnswers, null);
      if (priorKey && Object.keys(priorAnswers).length > 0) setResumed(true);
      setCurrentQid(firstQ === SCREENED_OUT || firstQ === END ? null : firstQ);
      setPhase("question");
    } catch (e) {
      setErrorMsg(e instanceof ApiError ? e.message : "Could not start the survey.");
      setPhase("error");
    }
  }

  function setAnswer(qid: string, value: unknown) {
    const next = { ...answers, [qid]: value };
    setAnswers(next);
    if (resumeKey) {
      localStorage.setItem(storageKey(token), JSON.stringify({ resume_key: resumeKey, answers: next }));
      scheduleSave(resumeKey, next);
    }
  }

  async function advance() {
    if (!currentQid || !resumeKey) return;
    const q = questionById(structure, currentQid);
    if (q?.required && isEmpty(answers[currentQid])) return;
    // flush pending save before navigating
    await publicSurveyApi.save(token, resumeKey, answers).catch(() => {});
    const nxt = nextQuestionId(structure, answers, currentQid);
    if (nxt === END || nxt === SCREENED_OUT) {
      await finish();
    } else {
      setCurrentQid(nxt);
    }
  }

  function back() {
    if (!currentQid) return;
    const order = orderedQids(structure);
    const idx = order.indexOf(currentQid);
    if (idx > 0) setCurrentQid(order[idx - 1]);
  }

  async function finish() {
    if (!resumeKey) return;
    try {
      const res = await publicSurveyApi.complete(token, resumeKey);
      setEnding(res.status);
      localStorage.removeItem(storageKey(token));
      setPhase("done");
    } catch (e) {
      // required-missing or other; keep them in the flow
      setErrorMsg(e instanceof ApiError ? e.message : "Please complete all required questions.");
    }
  }

  // ----------------------------- render -----------------------------

  if (phase === "loading") return <Shell><p className="text-ink/50">Loading…</p></Shell>;

  if (phase === "error")
    return (
      <Shell>
        <h1 className="font-display text-xl text-forest">Survey unavailable</h1>
        <p className="mt-2 text-ink/60">{errorMsg}</p>
      </Shell>
    );

  if (phase === "welcome")
    return (
      <Shell>
        <h1 className="font-display text-2xl text-forest">{survey?.title}</h1>
        <p className="mt-2 text-ink/60">
          Thanks for taking part. Your answers save automatically as you go.
        </p>
        <button
          onClick={start}
          className="mt-6 w-full rounded-xl bg-leaf py-3 text-white hover:bg-leaf/90"
        >
          Start
        </button>
      </Shell>
    );

  if (phase === "done") return <Shell><EndScreen ending={ending} /></Shell>;

  // question phase
  const q = currentQid ? questionById(structure, currentQid) : null;
  const order = orderedQids(structure);
  const progress = currentQid ? (order.indexOf(currentQid) + 1) / Math.max(1, order.length) : 0;
  const isLast = q ? nextQuestionId(structure, answers, q.id) === END : false;

  return (
    <Shell>
      {resumed && (
        <div className="mb-3 rounded-lg bg-leaf/10 px-3 py-2 text-sm text-forest">
          Welcome back — resuming where you left off.
        </div>
      )}
      <div className="mb-4 h-1.5 rounded-full bg-bg">
        <div className="h-1.5 rounded-full bg-leaf transition-all" style={{ width: `${progress * 100}%` }} />
      </div>
      {q && (
        <div>
          <label className="block font-display text-lg text-forest">
            {q.text}
            {q.required && <span className="text-leaf"> *</span>}
          </label>
          <div className="mt-4">
            <QuestionInput
              question={q}
              value={answers[q.id]}
              onChange={(v) => setAnswer(q.id, v)}
            />
          </div>
          {errorMsg && <p className="mt-3 text-sm text-red-600">{errorMsg}</p>}
          <div className="mt-6 flex gap-3">
            {order.indexOf(q.id) > 0 && (
              <button
                onClick={back}
                className="rounded-xl border border-line px-5 py-3 text-forest hover:bg-bg"
              >
                Back
              </button>
            )}
            <button
              onClick={advance}
              disabled={q.required && isEmpty(answers[q.id])}
              className="flex-1 rounded-xl bg-leaf py-3 text-white hover:bg-leaf/90 disabled:opacity-40"
            >
              {isLast ? "Submit" : "Next"}
            </button>
          </div>
        </div>
      )}
    </Shell>
  );
}

// ----------------------------- pieces -----------------------------

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center bg-bg px-4 py-10">
      <div className="w-full max-w-md rounded-3xl border border-line bg-white p-6 shadow-sm">
        {children}
      </div>
      <p className="mt-6 text-xs text-ink/40">Powered by Laboratree · Grow · Innovate · Impact</p>
    </div>
  );
}

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: FieldQuestion;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (question.type === "single")
    return (
      <div className="space-y-2">
        {(question.options ?? []).map((opt) => (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={`w-full rounded-xl border px-4 py-3 text-left ${
              value === opt ? "border-leaf bg-leaf/10 text-forest" : "border-line hover:bg-bg"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    );

  if (question.type === "multi") {
    const arr = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="space-y-2">
        {(question.options ?? []).map((opt) => {
          const on = arr.includes(opt);
          return (
            <button
              key={opt}
              onClick={() => onChange(on ? arr.filter((o) => o !== opt) : [...arr, opt])}
              className={`w-full rounded-xl border px-4 py-3 text-left ${
                on ? "border-leaf bg-leaf/10 text-forest" : "border-line hover:bg-bg"
              }`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    );
  }

  if (question.type === "scale") {
    const min = question.scale?.min ?? 1;
    const max = question.scale?.max ?? 5;
    const opts = Array.from({ length: max - min + 1 }, (_, i) => min + i);
    return (
      <div className="flex flex-wrap gap-2">
        {opts.map((n) => (
          <button
            key={n}
            onClick={() => onChange(n)}
            className={`h-12 w-12 rounded-full border text-sm ${
              value === n ? "border-leaf bg-leaf text-white" : "border-line hover:bg-bg"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    );
  }

  if (question.type === "number")
    return (
      <input
        type="number"
        value={value === undefined ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
        className="w-full rounded-xl border border-line px-4 py-3"
      />
    );

  return (
    <textarea
      value={value === undefined ? "" : String(value)}
      onChange={(e) => onChange(e.target.value)}
      rows={4}
      className="w-full rounded-xl border border-line px-4 py-3"
      placeholder="Your answer…"
    />
  );
}

function EndScreen({ ending }: { ending: Ending }) {
  const copy: Record<Ending, { title: string; body: string }> = {
    accepted: { title: "Thank you!", body: "Your response has been recorded. We appreciate your time." },
    screened_out: {
      title: "Thanks for your interest",
      body: "Based on your answers, this study isn't a fit — but we're grateful you started.",
    },
    quota_full: {
      title: "This group is full",
      body: "We've already heard from enough people like you. Thank you for your time!",
    },
  };
  const c = copy[ending];
  return (
    <div className="text-center">
      <div className="text-4xl">🌱</div>
      <h1 className="mt-3 font-display text-2xl text-forest">{c.title}</h1>
      <p className="mt-2 text-ink/60">{c.body}</p>
    </div>
  );
}

// ----------------------------- helpers -----------------------------

function questionById(structure: SurveyStructure, qid: string): FieldQuestion | null {
  for (const s of structure.sections) for (const q of s.questions) if (q.id === qid) return q;
  return null;
}

function isEmpty(v: unknown): boolean {
  return v === undefined || v === "" || (Array.isArray(v) && v.length === 0);
}

function firstUnansweredOrFirst(
  structure: SurveyStructure,
  answers: Record<string, unknown>,
): string {
  let current = nextQuestionId(structure, answers, null);
  while (current !== END && current !== SCREENED_OUT) {
    if (isEmpty(answers[current])) return current;
    current = nextQuestionId(structure, answers, current);
  }
  return nextQuestionId(structure, {}, null);
}
