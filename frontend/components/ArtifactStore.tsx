"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { artifactStoreApi, storageApi, type StoreArtifact } from "@/lib/api";

// One place for everything the labs and agents produced — snapshots, traces, workbooks,
// figures — grouped by the lab that made them, every entry downloadable with provenance.

const KIND_ICON: Record<string, string> = {
  page: "🌐", trace: "🧠", workbook: "📊", figure: "📈", model: "🤖", file: "📄",
};

function prettySize(bytes: number): string {
  if (!bytes) return "—";
  return bytes > 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${(bytes / 1024).toFixed(1)} kB`;
}

export default function ArtifactStore({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<StoreArtifact[]>([]);
  const [labFilter, setLabFilter] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setItems(await artifactStoreApi.list(projectId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load artifacts");
    }
  }, [projectId]);

  useEffect(() => { void refresh(); }, [refresh]);

  const labs = useMemo(
    () => [...new Set(items.map((i) => i.lab).filter(Boolean))].sort(), [items]);
  const shown = labFilter ? items.filter((i) => i.lab === labFilter) : items;

  async function open(item: StoreArtifact) {
    try {
      if (item.origin === "run" && item.artifact_id) {
        await artifactStoreApi.openRunArtifact(item.artifact_id);
      } else {
        await storageApi.open(item.key);
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
          Everything your labs and agents produced — page snapshots, agent traces, workbooks,
          figures — in one browsable, downloadable place, grouped by the lab that made it.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <button onClick={() => setLabFilter("")}
            className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
              labFilter === "" ? "bg-leaf text-forest" : "bg-white/15 text-white hover:bg-white/25"}`}>
            all · {items.length}
          </button>
          {labs.map((lab) => (
            <button key={lab} onClick={() => setLabFilter(lab)}
              className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
                labFilter === lab ? "bg-leaf text-forest" : "bg-white/15 text-white hover:bg-white/25"}`}>
              {lab} · {items.filter((i) => i.lab === lab).length}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="rounded-2xl border border-line bg-white p-4">
        {shown.length === 0 ? (
          <p className="text-sm text-ink/50">
            Nothing here yet — run a lab, a SpiderWeb mission, or a supervised flow and its
            outputs will land here automatically.
          </p>
        ) : (
          <div className="space-y-1.5">
            {shown.map((item, i) => (
              <div key={`${item.key}-${i}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2 transition hover:border-leaf/60">
                <div className="min-w-0">
                  <button onClick={() => void open(item)}
                    className="block max-w-full truncate text-left text-sm font-semibold text-forest hover:underline"
                    title={item.key}>
                    {KIND_ICON[item.kind] ?? "📄"} {item.name}
                  </button>
                  <p className="truncate text-[11px] text-ink/60" title={item.description}>
                    {item.description || item.source || item.key}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span className="rounded-full bg-bg px-2 py-0.5 text-[10px] font-bold text-forest">
                    {item.lab}
                  </span>
                  <p className="mt-0.5 text-[10px] text-ink/40">
                    {prettySize(item.size)} · {item.created_at.slice(0, 16).replace("T", " ")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
