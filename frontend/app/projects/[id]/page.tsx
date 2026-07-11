"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Api, openBlob, type Project } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { LAB_TAB_GROUPS, labTabLabel, labTabShort, type LabTabKey } from "@/lib/labTabs";

// Each Lab is loaded on demand (only when its tab is opened) so the project page opens fast and
// heavy deps (React Flow, vega, papaparse) aren't pulled into the initial route bundle.
const TabLoading = () => (
  <div className="space-y-3" role="status" aria-label="Loading lab">
    <div className="h-24 animate-shimmer rounded-2xl" />
    <div className="h-64 animate-shimmer rounded-2xl" />
  </div>
);
const dyn = (loader: () => Promise<{ default: React.ComponentType<{ projectId: string }> }>) =>
  dynamic(loader, { ssr: false, loading: TabLoading });

const SignalLab = dyn(() => import("@/components/SignalLab"));
const PapersLab = dyn(() => import("@/components/PapersLab"));
const InsightLab = dyn(() => import("@/components/InsightLab"));
const IdeationLab = dyn(() => import("@/components/IdeationLab"));
const CollectionLab = dyn(() => import("@/components/CollectionLab"));
const FieldLab = dyn(() => import("@/components/FieldLab"));
const PanelLab = dyn(() => import("@/components/PanelLab"));
const QualLab = dyn(() => import("@/components/QualLab"));
const DeliverablesLab = dyn(() => import("@/components/DeliverablesLab"));
const PersonaLab = dyn(() => import("@/components/PersonaLab"));
const PipelineLab = dynamic(() => import("@/components/pipeline/PipelineLab"), {
  ssr: false,
  loading: TabLoading,
});
const LlmActivity = dyn(() => import("@/components/LlmActivity"));
const SpiderWebLab = dyn(() => import("@/components/SpiderWebLab"));
const LearningLab = dyn(() => import("@/components/LearningLab"));

type TabKey = LabTabKey;

export default function ProjectWorkspace() {
  const { user, loading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [project, setProject] = useState<Project | null>(null);
  const [tab, setTab] = useState<TabKey>("signal");
  const [error, setError] = useState<string | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [trustScore, setTrustScore] = useState<number | null>(null);

  async function makeReport() {
    setReportBusy(true);
    try {
      const r = await Api.generateReport(projectId);
      setTrustScore(r.trust.score);
      await openBlob(r.download_url);
    } catch {
      /* ignore */
    } finally {
      setReportBusy(false);
    }
  }

  useEffect(() => {
    if (user && projectId) {
      Api.getProject(projectId)
        .then(setProject)
        .catch((e) => setError(e instanceof Error ? e.message : "failed"));
    }
  }, [user, projectId]);

  if (loading || !user) return <p className="text-muted">Loading…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  const activeGroup = LAB_TAB_GROUPS.find((g) => g.tabs.includes(tab));

  return (
    <div>
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link href="/" className="hover:text-forest">Projects</Link>
        <span className="mx-1.5 text-line">/</span>
        <span className="text-forest">{project?.name ?? "…"}</span>
      </nav>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl text-forest">{project?.name ?? "…"}</h1>
          <p className="mt-1 text-sm text-muted">
            {activeGroup ? (
              <>
                <span style={{ color: activeGroup.accent }}>◆</span>{" "}
                {activeGroup.title} · {labTabLabel(tab)}
              </>
            ) : (
              "Research workspace"
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {trustScore !== null && (
            <span
              className="rounded-full bg-leaf/15 px-3 py-1.5 text-sm font-semibold text-forest"
              title="Trust score from the latest report — provenance, reproducibility and leakage checks"
            >
              🔒 trust {trustScore}/100
            </span>
          )}
          <button
            onClick={makeReport}
            disabled={reportBusy}
            className="rounded-full bg-forest px-5 py-2 text-sm font-semibold text-white shadow-[0_2px_10px_rgba(20,52,42,0.25)] transition hover:-translate-y-px hover:opacity-90 disabled:opacity-50 disabled:shadow-none"
          >
            {reportBusy ? "Building report…" : "Report card"}
          </button>
        </div>
      </div>

      <div className="relative mt-6">
        <nav
          aria-label="Labs by lifecycle phase"
          className="no-scrollbar overflow-x-auto rounded-2xl border border-line bg-white px-4 py-3"
        >
          <div className="flex min-w-max items-stretch gap-3">
            {LAB_TAB_GROUPS.map((group, gi) => (
              <div key={group.key} className="flex items-stretch gap-3">
                {gi > 0 && <span className="w-px self-stretch bg-line" />}
                <div>
                  <div
                    className="text-[9px] font-extrabold uppercase tracking-[0.14em]"
                    style={{ color: group.accent }}
                  >
                    ◆ {group.title}
                  </div>
                  <div className="mt-1.5 flex gap-0.5">
                    {group.tabs.map((key) => {
                      const active = tab === key;
                      return (
                        <button
                          key={key}
                          onClick={() => setTab(key)}
                          title={labTabLabel(key)}
                          aria-current={active ? "page" : undefined}
                          className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium transition ${
                            active
                              ? "bg-forest text-white shadow-sm"
                              : "text-muted hover:bg-bg hover:text-forest"
                          }`}
                          style={active ? { boxShadow: `inset 0 2px 0 ${group.accent}` } : undefined}
                        >
                          {labTabShort(key)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </nav>
        <span
          aria-hidden
          className="pointer-events-none absolute inset-y-1 right-1 w-8 rounded-r-2xl bg-gradient-to-l from-white to-transparent xl:hidden"
        />
      </div>

      <div className="mt-6">
        {tab === "ideation" && <IdeationLab projectId={projectId} />}
        {tab === "collection" && <CollectionLab projectId={projectId} />}
        {tab === "field" && <FieldLab projectId={projectId} />}
        {tab === "panel" && <PanelLab projectId={projectId} />}
        {tab === "personas" && <PersonaLab projectId={projectId} />}
        {tab === "qual" && <QualLab projectId={projectId} />}
        {tab === "signal" && <SignalLab projectId={projectId} />}
        {tab === "insight" && <InsightLab projectId={projectId} />}
        {tab === "papers" && <PapersLab projectId={projectId} />}
        {tab === "learning" && <LearningLab projectId={projectId} />}
        {tab === "deliver" && <DeliverablesLab projectId={projectId} />}
        {tab === "pipeline" && <PipelineLab projectId={projectId} onOpenLab={setTab} />}
        {tab === "spiderweb" && <SpiderWebLab projectId={projectId} />}
        {tab === "llm" && <LlmActivity projectId={projectId} />}
      </div>
    </div>
  );
}
