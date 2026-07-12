"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  artifactStoreApi,
  storageApi,
  type StoreArtifact,
  type StoreTaskGroup,
} from "@/lib/api";

// Artifact Store — everything the labs and agents produced, grouped by the TASK that produced
// it. One collapsible card per run/mission/chat/flow (labelled by its objective), so it reads
// as a list of tasks with their outputs — not a flat dump.

const KIND_ICON: Record<string, string> = {
  page: "🌐", pdf: "📕", trace: "🧠", workbook: "📊", figure: "📈", model: "🤖", file: "📄",
};

const TASK_META: Record<string, { icon: string; label: string }> = {
  mission: { icon: "🕸️", label: "SpiderWeb mission" },
  chat: { icon: "💬", label: "Chat task" },
  flow: { icon: "🔀", label: "Pipeline flow" },
  run: { icon: "⚙️", label: "Component run" },
  media: { icon: "🎬", label: "Media" },
  other: { icon: "📁", label: "Other" },
};

function prettySize(bytes: number): string {
  if (!bytes) return "—";
  return bytes > 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${(bytes / 1024).toFixed(1)} kB`;
}

function timeAgo(iso: string): string {
  const d = new Date(iso.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 16).replace("T", " ");
}

function TaskCard({ group, onOpen }: {
  group: StoreTaskGroup;
  onOpen: (a: StoreArtifact) => void;
}) {
  const [open, setOpen] = useState(false);
  const meta = TASK_META[group.task_kind] ?? TASK_META.other;
  return (
    <div className="rounded-xl border border-line bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
      >
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-base">{meta.icon}</span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-forest" title={group.label}>
              {group.label}
            </p>
            <p className="text-[10px] text-ink/50">
              {meta.label}
              {group.lab ? ` · ${group.lab}` : ""} · {timeAgo(group.created_at)}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="rounded-full bg-bg px-2 py-0.5 text-[10px] font-bold text-forest">
            {group.count} file{group.count === 1 ? "" : "s"}
          </span>
          <span className="text-[10px] text-ink/40">{open ? "▲" : "▼"}</span>
        </div>
      </button>
      {open && (
        <div className="space-y-1 border-t border-line px-3 py-2">
          {group.artifacts.map((a, i) => (
            <div key={`${a.key}-${i}`} className="flex items-center justify-between gap-2">
              <button
                onClick={() => onOpen(a)}
                className="flex min-w-0 items-center gap-1.5 text-left"
                title={a.description || a.key}
              >
                <span>{KIND_ICON[a.kind] ?? "📄"}</span>
                <span className="truncate text-[12px] text-[#2563EB] hover:underline">
                  {a.name}
                </span>
              </button>
              <span className="shrink-0 text-[10px] text-ink/40">{prettySize(a.size)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ArtifactStore({ projectId }: { projectId: string }) {
  const [groups, setGroups] = useState<StoreTaskGroup[]>([]);
  const [labs, setLabs] = useState<string[]>([]);
  const [labFilter, setLabFilter] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await artifactStoreApi.list(projectId);
      setGroups(r.groups);
      setLabs(r.labs);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load artifacts");
    }
  }, [projectId]);

  useEffect(() => { void refresh(); }, [refresh]);

  const shown = useMemo(
    () => (labFilter ? groups.filter((g) => g.lab === labFilter) : groups),
    [groups, labFilter]);

  async function open(a: StoreArtifact) {
    try {
      if (a.origin === "run" && a.artifact_id) {
        await artifactStoreApi.openRunArtifact(a.artifact_id);
      } else {
        await storageApi.open(a.key);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "download failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-line bg-gradient-to-r from-forest to-[#1F5A43] p-5">
        <h2 className="font-display text-xl text-white">🗄️ Artifact Store</h2>
        <p className="mt-1 text-xs text-white/70">
          Every task&apos;s outputs in one place — grouped by the run, mission, chat or flow that
          produced them. Open a task to browse and download its files, each with provenance.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <button
            onClick={() => setLabFilter("")}
            className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
              labFilter === "" ? "bg-leaf text-forest" : "bg-white/15 text-white hover:bg-white/25"}`}
          >
            all · {groups.length}
          </button>
          {labs.map((lab) => (
            <button
              key={lab}
              onClick={() => setLabFilter(lab)}
              className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
                labFilter === lab ? "bg-leaf text-forest" : "bg-white/15 text-white hover:bg-white/25"}`}
            >
              {lab} · {groups.filter((g) => g.lab === lab).length}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {shown.length === 0 ? (
        <div className="rounded-2xl border border-line bg-white p-4">
          <p className="text-sm text-ink/50">
            Nothing here yet — run a lab task, a SpiderWeb mission, or a supervised flow and its
            outputs will appear here, grouped by task.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {shown.map((g) => (
            <TaskCard key={g.task_id} group={g} onOpen={open} />
          ))}
        </div>
      )}
    </div>
  );
}
