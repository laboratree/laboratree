"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import LabChat from "@/components/LabChat";

// Research OS — the Research Director console. One question in; the Director discovers
// literature, pulls + reads open-access PDFs, extracts and verifies claims, seeks
// corroborating and contradictory evidence, and synthesizes an evidence-backed answer,
// streaming every step. The Co-Scientist (hypothesis generation) lives here as a studio.
const IdeationLab = dynamic(() => import("@/components/IdeationLab"));

const EXAMPLES = [
  "Find the seminal papers on women's economic empowerment that use an econometric model, and summarize what each measures.",
  "What does the evidence say about cash transfers vs. in-kind aid for school attendance? Corroborate and contradict.",
  "Map the state of the art in graph-based retrieval for multi-hop QA, with the strongest benchmarks.",
];

export default function ResearchOS({ projectId }: { projectId: string }) {
  const [studioOpen, setStudioOpen] = useState(false);

  return (
    <div className="space-y-4">
      {/* Director hero */}
      <div className="overflow-hidden rounded-2xl border border-line bg-gradient-to-br from-[#0B1E17] via-forest to-[#1F5A43] p-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🧭</span>
          <h2 className="font-display text-2xl text-white">Research OS</h2>
          <span className="rounded-full bg-white/15 px-2.5 py-0.5 text-[11px] font-bold text-[#A8D08D]">
            Research Director
          </span>
        </div>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Ask a research question. The Director plans the investigation, discovers literature
          (papers, arXiv, the open web), pulls and reads the open-access PDFs, extracts and
          verifies claims against their sources, hunts corroborating <em>and</em> contradictory
          evidence, then synthesizes a cited answer — streaming every thought and Evidence-locking
          every conclusion. It never fabricates a figure or a source.
        </p>
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#A8D08D]">
            Try asking
          </p>
          <ul className="mt-1 space-y-1">
            {EXAMPLES.map((ex) => (
              <li key={ex} className="text-xs text-white/60">
                <span className="mr-1 text-[#6DB33F]">›</span>{ex}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* the Director console — streamed plan → discover → read → verify → cited report */}
      <LabChat
        projectId={projectId}
        lab="ideation"
        title="Research Director"
        startOpen
        intro="Ask a research question and the Director will investigate end-to-end — you'll see it plan, discover papers, read PDFs, verify claims, and synthesize a cited answer, live."
      />

      {/* Hypothesis Studio — the grounded Co-Scientist, folded in (nothing lost) */}
      <div className="rounded-2xl border border-line bg-white">
        <button
          onClick={() => setStudioOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <span className="font-display text-lg text-forest">
            🔬 Hypothesis Studio
            <span className="ml-2 text-xs font-normal text-ink/50">
              Co-Scientist — turn a question into ranked, testable hypotheses
            </span>
          </span>
          <span className="text-xs text-[#2563EB]">{studioOpen ? "hide" : "open"}</span>
        </button>
        {studioOpen && (
          <div className="border-t border-line p-4">
            <IdeationLab projectId={projectId} />
          </div>
        )}
      </div>
    </div>
  );
}
