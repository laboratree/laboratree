"use client";

import { useEffect, useState } from "react";
import { Api, type Lesson } from "@/lib/api";
import LessonPlayer from "@/components/lesson/LessonPlayer";
import { DataStage, stagesFor } from "@/components/model-viz";
import { ParamPanel } from "@/components/model-viz/param-panel";
import { TestTable } from "@/components/model-viz/test-table";

/**
 * Model walkthrough on the REAL data. Two views over ONE fetched lesson:
 *  - Guided show (default): the cinematic LessonPlayer — narrated chapters, transport bar,
 *    scrubbable steps (components/lesson/).
 *  - Classic: the original 3-tab staged view (data / training / testing) over the same trace.
 * The hyperparameter panel re-fits the lesson live in either view.
 */

type View = "show" | "classic";
type Phase = "data" | "train" | "test";

export default function StagedModelAnimation({
  datasetId,
  target,
  family,
  title,
  initialParams,
  onSaveVariant,
  theater = false,
  exampleModel,
}: {
  datasetId: string;
  target: string;
  family: string;
  title?: string; // the paper's model name — resolves the lesson (XGBoost → the xgboost script)
  initialParams?: Record<string, number | string | string[]>; // the paper's hyperparameters (defaults)
  // save the current knob settings as a NEW model branch that competes on the leaderboard
  onSaveVariant?: (params: Record<string, number | string | string[]>) => void;
  theater?: boolean; // Learning Lab full-width mode
  // when set, fit on the MODEL'S OWN example dataset (Learning Lab default) instead of datasetId
  exampleModel?: string;
}) {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [view, setView] = useState<View>("show");
  const [phase, setPhase] = useState<Phase>("data"); // classic view tabs
  const [rowIdx, setRowIdx] = useState(0);
  // live hyperparameter overrides (start from the paper's, user can tweak → re-fit)
  const [params, setParams] = useState<Record<string, number | string | string[]>>(initialParams ?? {});
  const seed = JSON.stringify(initialParams ?? {});
  const model = title || family; // free text; the backend resolves it to a lesson

  // switching node/dataset/model resets the view and the knobs back to the paper's defaults
  useEffect(() => {
    setPhase("data");
    setRowIdx(0);
    setParams(initialParams ? { ...initialParams } : {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, target, model, seed, exampleModel]);

  // (re)fit whenever inputs or the knobs change — but DON'T bounce the user off their current view
  const paramsKey = JSON.stringify(params);
  useEffect(() => {
    let alive = true;
    setBusy(true);
    setErr(null);
    const id = setTimeout(() => {
      // example mode: fit on the model's own built-in dataset; else the given dataset
      const p = exampleModel
        ? Api.modelExampleLesson(exampleModel, params)
        : Api.modelLesson(datasetId, target, model, params);
      p.then((l) => alive && setLesson(l))
        .catch((e) => alive && setErr(e instanceof Error ? e.message : "lesson failed"))
        .finally(() => alive && setBusy(false));
    }, 220); // debounce slider drags
    return () => {
      alive = false;
      clearTimeout(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, target, model, paramsKey, exampleModel]);

  // first-ever load (no lesson yet) shows the full loader; later re-fits keep the panel + a badge
  if (busy && !lesson)
    return (
      <div className="rounded-xl border border-line bg-bg p-4 text-xs text-muted">
        Training a small model on the real data…
      </div>
    );
  if (err || !lesson)
    return (
      <div className="rounded-xl border border-line bg-bg p-3 text-xs text-muted">
        Couldn&apos;t build the walkthrough{err ? ` (${err})` : ""}. Generate data first.
      </div>
    );

  const trace = lesson.trace;
  const { Train, Test } = stagesFor(trace.family);
  const rows = trace.test_rows ?? [];
  const row = rows[Math.min(rowIdx, Math.max(0, rows.length - 1))];

  return (
    <div className="rounded-xl border border-line bg-gradient-to-b from-white to-[#F6FAF2] p-3">
      {/* view switch + re-fit badge */}
      <div className="mb-2 flex items-center gap-1 text-xs">
        {(
          [
            ["show", "▶ Guided show"],
            ["classic", "☰ Classic"],
          ] as [View, string][]
        ).map(([v, label]) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`rounded-lg px-2.5 py-1 font-medium transition ${
              view === v ? "bg-forest text-white" : "border border-line text-forest hover:bg-bg"
            }`}
          >
            {label}
          </button>
        ))}
        <span className="ml-2 hidden text-[10px] text-muted sm:inline">
          {view === "show" ? `${lesson.title} · ${Math.round(lesson.total_ms / 60000)} min guided lesson` : ""}
        </span>
        {busy && <span className="ml-auto animate-pulse text-[10px] text-[#8a6d1a]">re-fitting…</span>}
      </div>

      <ParamPanel
        spec={lesson.param_spec ?? trace.param_spec ?? []}
        paperDefaults={initialParams}
        onChange={(k, v) => setParams((prev) => ({ ...prev, [k]: v }))}
        onReset={() => setParams(initialParams ? { ...initialParams } : {})}
        onSaveVariant={onSaveVariant ? () => onSaveVariant(params) : undefined}
      />

      {view === "show" && <LessonPlayer lesson={lesson} hint={title} theater={theater} />}

      {view === "classic" && (
        <>
          <div className="mb-2 flex items-center gap-1 text-xs">
            {(
              [
                ["data", "1 · The data"],
                ["train", "2 · Training"],
                ["test", "3 · Testing"],
              ] as [Phase, string][]
            ).map(([p, label]) => (
              <button
                key={p}
                onClick={() => setPhase(p)}
                className={`rounded-lg px-2.5 py-1 font-medium transition ${
                  phase === p ? "bg-forest text-white" : "border border-line text-forest hover:bg-bg"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {phase === "data" && <DataStage trace={trace} />}
          {phase === "train" && <Train trace={trace} hint={title} />}
          {phase === "test" && row && (
            <TestTable
              trace={trace}
              rows={rows}
              rowIdx={rowIdx}
              setRowIdx={setRowIdx}
              Test={Test}
              hint={title}
            />
          )}
          <p className="mt-2 text-[11px] text-muted">{trace.note}</p>
        </>
      )}
    </div>
  );
}
