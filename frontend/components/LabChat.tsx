"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  labAgentsApi,
  type AgentRunView,
  type AgentStep,
  type ChatMessageView,
  type FlowOp,
} from "@/lib/api";

// One conversational agent per Lab: chat answers grounded questions, spawns live agent runs
// for work (plan → todo checklist → tool steps → findings), and — for the pipeline agent —
// returns flow_ops the canvas applies via onFlowOps.
export type LabChatProps = {
  projectId: string;
  lab: string;
  title?: string;
  onFlowOps?: (ops: FlowOp[]) => void;
};

const POLL_MS = 2000;

function StepLine({ step }: { step: AgentStep }) {
  if (step.kind === "plan") {
    return (
      <div className="mt-1 rounded-lg bg-[#F3EEFB] p-2 text-[11px] text-[#6D28D9]">
        📋 Plan: {(step.todos ?? []).map((t) => t.objective).join(" · ")}
      </div>
    );
  }
  if (step.kind === "todo") {
    const icon = step.status === "done" ? "✅" : step.status === "running" ? "⏳" : "🔲";
    return (
      <div className="mt-1 text-[11px] text-ink/70">
        {icon} {step.objective ?? step.summary ?? `task ${step.id}`}
        {step.status === "done" && step.summary ? ` — ${step.summary}` : ""}
      </div>
    );
  }
  if (step.kind === "critic") {
    return (
      <div className="mt-1 text-[11px] text-amber-700">
        🧐 critic dropped {step.dropped} unsupported finding{step.dropped === 1 ? "" : "s"}
      </div>
    );
  }
  return (
    <div className="mt-1 rounded-lg bg-bg p-2 text-[11px]">
      <span className="text-ink/60">💭 {step.thought}</span>
      <div className="mt-0.5 font-mono text-[10px] text-forest">
        ⚙ {step.tool}({step.args})
      </div>
      <div className="mt-0.5 max-h-16 overflow-hidden text-[10px] text-ink/50">
        → {step.observation}
      </div>
    </div>
  );
}

function RunView({ projectId, agentRunId }: { projectId: string; agentRunId: string }) {
  const [run, setRun] = useState<AgentRunView | null>(null);

  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const r = await labAgentsApi.run(projectId, agentRunId);
        if (!live) return;
        setRun(r);
        if (r.status === "queued" || r.status === "running") timer = setTimeout(tick, POLL_MS);
      } catch {
        /* transient poll errors are fine */
      }
    };
    void tick();
    return () => { live = false; clearTimeout(timer); };
  }, [projectId, agentRunId]);

  if (!run) return <p className="mt-1 text-[11px] text-ink/40">starting…</p>;
  return (
    <div className="mt-1">
      {run.steps.map((s, i) => <StepLine key={i} step={s} />)}
      {run.status === "succeeded" && run.findings.length > 0 && (
        <div className="mt-2 rounded-lg border border-leaf/40 bg-leaf/10 p-2">
          {run.findings.map((f, i) => (
            <p key={i} className="text-[11px] text-forest">
              🔒 {String(f.claim ?? "")}
              {f.confidence != null && (
                <span className="ml-1 text-[10px] text-ink/50">
                  ({Math.round(Number(f.confidence) * 100)}%)
                </span>
              )}
            </p>
          ))}
        </div>
      )}
      {run.status === "gated" && (
        <p className="mt-1 text-[11px] text-amber-700">⏸ {run.summary}</p>
      )}
      {run.status === "failed" && (
        <p className="mt-1 text-[11px] text-red-600">✕ {run.summary}</p>
      )}
      <p className="mt-1 text-[10px] text-ink/40">
        {run.status} · {run.llm_calls} calls
        {run.tokens ? ` · ${run.tokens.toLocaleString()} tokens` : ""}
        {run.cost_usd ? ` · ~$${run.cost_usd.toFixed(3)}` : ""}
      </p>
    </div>
  );
}

export default function LabChat({ projectId, lab, title, onFlowOps }: LabChatProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    const message = input.trim();
    if (!message || busy) return;
    setBusy(true);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: message }]);
    try {
      const r = await labAgentsApi.chat(projectId, lab, message, threadId ?? undefined);
      setThreadId(r.thread_id);
      setMessages((m) => [...m, {
        role: "agent", content: r.reply, agent_run_id: r.agent_run_id ?? undefined,
      }]);
      if (r.flow_ops?.length && onFlowOps) onFlowOps(r.flow_ops);
    } catch (e) {
      setMessages((m) => [...m, {
        role: "agent",
        content: e instanceof Error ? `error: ${e.message}` : "something went wrong",
      }]);
    } finally {
      setBusy(false);
    }
  }, [input, busy, projectId, lab, threadId, onFlowOps]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="mb-4 flex w-full items-center justify-between rounded-2xl border border-line bg-white px-4 py-2.5 text-left transition hover:border-leaf"
      >
        <span className="text-sm font-semibold text-forest">
          💬 Chat with the {title ?? `${lab} agent`}
        </span>
        <span className="text-xs text-ink/40">
          grounded answers · delegated agent runs · live steps
        </span>
      </button>
    );
  }

  return (
    <div className="mb-4 overflow-hidden rounded-2xl border border-line bg-white">
      <div className="flex items-center justify-between bg-gradient-to-r from-forest to-[#1F5A43] px-4 py-2">
        <span className="text-sm font-bold text-white">💬 {title ?? `${lab} agent`}</span>
        <button onClick={() => setOpen(false)} className="text-xs text-white/60 hover:text-white">
          collapse
        </button>
      </div>
      <div className="max-h-96 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-xs text-ink/40">
            Ask anything, or delegate work — the agent grounds its answers in your project&apos;s
            data and Evidence-locks what it produces.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block max-w-[90%] rounded-xl px-3 py-2 text-left text-sm ${
              m.role === "user" ? "bg-forest text-white" : "bg-bg text-ink"
            }`}>
              {m.content}
              {m.agent_run_id && (
                <RunView projectId={projectId} agentRunId={m.agent_run_id} />
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="flex gap-2 border-t border-line p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") void send(); }}
          placeholder="Ask, delegate, or give feedback…"
          className="flex-1 rounded-lg border border-line px-3 py-1.5 text-sm"
        />
        <button
          onClick={() => void send()}
          disabled={busy || !input.trim()}
          className="rounded-lg bg-leaf px-4 py-1.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
