"use client";

import LabChat from "@/components/LabChat";
import { useEffect, useMemo, useState } from "react";
import {
  Api,
  type DatasetSummary,
  type ExampleMeta,
  type LessonCatalogEntry,
} from "@/lib/api";
import StagedModelAnimation from "@/components/StagedModelAnimation";

/**
 * Learning Lab — every model Laboratree knows, taught as a guided live show.
 * Each model DEFAULTS to its own built-in example dataset (regression → house prices,
 * CNN → tiny cat/dog images, ARIMA → a monthly series, clustering → customer segments …) so
 * it's always taught on data that actually fits it. You can optionally switch a model to one of
 * your project datasets.
 */

export default function LearningLab({ projectId }: { projectId: string }) {
  const [catalog, setCatalog] = useState<LessonCatalogEntry[] | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [open, setOpen] = useState<LessonCatalogEntry | null>(null);
  const [example, setExample] = useState<ExampleMeta | null>(null);
  const [error, setError] = useState<string | null>(null);

  // "example" (the model's own dataset, default) or a chosen project dataset
  const [source, setSource] = useState<"example" | string>("example");
  const [columns, setColumns] = useState<string[]>([]);
  const [target, setTarget] = useState("");

  useEffect(() => {
    let alive = true;
    Api.modelCatalog()
      .then((cat) => alive && setCatalog(cat))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "failed to load"));
    Api.projectDatasets(projectId)
      .then((ds) => alive && setDatasets(ds))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [projectId]);

  // opening a model → default to its example dataset and fetch its label
  useEffect(() => {
    if (!open) return;
    setSource("example");
    let alive = true;
    Api.modelExample(open.key)
      .then((m) => alive && setExample(m))
      .catch(() => alive && setExample(null));
    return () => {
      alive = false;
    };
  }, [open]);

  // if the user switches to a project dataset, load its columns for the target picker
  useEffect(() => {
    if (source === "example") return;
    let alive = true;
    Api.datasetPreview(source, 5)
      .then((p) => {
        if (!alive) return;
        setColumns(p.columns);
        setTarget((cur) => (cur && p.columns.includes(cur) ? cur : (p.columns[p.columns.length - 1] ?? "")));
      })
      .catch(() => alive && setColumns([]));
    return () => {
      alive = false;
    };
  }, [source]);

  const groups = useMemo(() => {
    const by = new Map<string, LessonCatalogEntry[]>();
    for (const e of catalog ?? []) {
      const g = by.get(e.group) ?? [];
      g.push(e);
      by.set(e.group, g);
    }
    return [...by.entries()];
  }, [catalog]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!catalog) return <p className="text-sm text-muted">Loading the Learning Lab…</p>;

  const usingExample = source === "example";

  return (
    <div className="space-y-4">
      <LabChat projectId={projectId} lab="learning" />
      <div className="max-w-2xl">
        <h2 className="font-display text-3xl leading-tight text-forest">
          Watch any model learn —{" "}
          <span className="text-[#8a6d1a]">on the right data for it.</span>
        </h2>
        <p className="mt-1.5 text-sm text-muted">
          Open any of the {catalog.length} models below. Each comes with its OWN example
          dataset — a regression on house prices, a CNN on tiny cat/dog images, ARIMA on a
          monthly series — so it's always taught on data that fits. Slow, narrated, scrubbable.
        </p>
      </div>

      {/* theater */}
      {open && (
        <div className="rounded-2xl border-2 border-forest/20 bg-white p-4 shadow-sm">
          <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="font-display text-xl text-forest">{open.display_name}</h3>
              <p className="text-xs text-muted">{open.one_liner}</p>
            </div>
            <button
              onClick={() => setOpen(null)}
              className="rounded-lg border border-line px-2.5 py-1 text-sm text-forest hover:bg-bg"
              title="Close the lesson"
            >
              ✕ Close
            </button>
          </div>

          {/* data source: the model's example (default) or one of your datasets */}
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-line bg-bg px-3 py-2 text-xs">
            <span className="font-medium text-forest">Data</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="rounded border border-line px-2 py-1"
            >
              <option value="example">
                ★ Example: {example?.name ?? `${open.display_name} sample`}
              </option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  my data · {d.name}
                  {d.n_rows ? ` (${d.n_rows} rows)` : ""}
                </option>
              ))}
            </select>
            {usingExample ? (
              <span className="text-muted">
                built-in dataset chosen to fit {open.display_name} — predicting{" "}
                <b className="text-forest">{example?.target ?? "…"}</b>
              </span>
            ) : (
              <label className="flex items-center gap-1.5">
                <span className="text-muted">predicting</span>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="rounded border border-line px-2 py-1"
                >
                  {columns.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          {usingExample ? (
            <StagedModelAnimation
              key={`ex-${open.key}`}
              exampleModel={open.key}
              datasetId=""
              target=""
              family={open.family}
              title={open.key}
              theater
            />
          ) : target ? (
            <StagedModelAnimation
              key={`${open.key}-${source}-${target}`}
              datasetId={source}
              target={target}
              family={open.family}
              title={open.key}
              theater
            />
          ) : (
            <p className="text-xs text-muted">Pick a target column above.</p>
          )}
        </div>
      )}

      {/* catalog */}
      {groups.map(([group, entries]) => (
        <section key={group}>
          <h3 className="mb-2 flex items-baseline gap-2 font-display text-lg text-forest">
            {group}
            <span className="font-sans text-[10px] font-normal text-muted">
              {entries.length} {entries.length === 1 ? "lesson" : "lessons"}
            </span>
          </h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {entries.map((e) => {
              const active = open?.key === e.key;
              return (
                <button
                  key={e.key}
                  onClick={() => setOpen(e)}
                  className={`group rounded-xl border p-3 text-left transition ${
                    active
                      ? "border-[#C9A227] bg-[#FFFDF5]"
                      : "border-line bg-white hover:border-[#C9A227]/60 hover:shadow-sm"
                  }`}
                  title={`Play the ${e.display_name} lesson on its example dataset`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-forest">
                      <span
                        aria-hidden
                        className={`mr-1 text-[10px] ${
                          active ? "text-[#C9A227]" : "text-line transition group-hover:text-[#C9A227]"
                        }`}
                      >
                        ▶
                      </span>
                      {e.display_name}
                    </p>
                    <span
                      className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                        e.has_deep_lesson
                          ? "bg-[#FBF3D6] text-[#8a6d1a]"
                          : "bg-leaf/10 text-forest"
                      }`}
                    >
                      {e.has_deep_lesson ? "★ deep lesson" : "guided intro"}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted">{e.one_liner}</p>
                  <p className="mt-1.5 font-mono text-[10px] text-muted">
                    {active ? "now playing" : e.task}
                  </p>
                </button>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
