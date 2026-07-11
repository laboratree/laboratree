"use client";

import type { SplitTrial, XGBNode } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** THE show-piece: candidate splits audition one by one — similarity chips, gain, and a live
 *  leaderboard; the max-gain candidate is crowned at the end. Scrub to replay any audition. */
export default function SplitTrialsStage({ lesson, step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const ref = step.anim?.ref ?? {};
  const round = typeof ref.round === "number" ? ref.round : 0;
  const root = lesson.trace.boosting?.rounds?.[round]?.root;
  const trials = findNode(root, typeof ref.node === "string" ? ref.node : "r")?.trials ?? [];

  const k = useSubstep(clock, entryIdx, Math.max(1, trials.length));
  const seen = reducedMotion ? trials.length : k;
  if (!trials.length) return <p className="text-xs text-muted">No auditions at this node.</p>;

  return (
    <TrialsBoard
      trials={trials}
      gamma={lesson.trace.boosting?.gamma ?? 0}
      seen={seen}
    />
  );
}

/** The audition board: spotlight card + gain leaderboard. Reused by the tree view's
 *  per-node replay (click any branch to see ITS auditions). */
export function TrialsBoard({
  trials,
  gamma,
  seen,
}: {
  trials: SplitTrial[];
  gamma: number;
  seen: number;
}) {
  const cur = trials[Math.max(0, Math.min(trials.length, seen) - 1)];
  const done = seen >= trials.length;
  const board = trials
    .slice(0, Math.max(1, seen))
    .map((t, i) => ({ t, i }))
    .sort((a, b) => b.t.gain - a.t.gain)
    .slice(0, 6);
  const maxGain = Math.max(0.0001, ...board.map((b) => Math.abs(b.t.gain)));

  return (
    <div className="grid gap-2 md:grid-cols-2">
      {/* the audition under the spotlight */}
      <div className="rounded-lg border border-[#C9A227]/50 bg-[#FFFDF5] p-2.5">
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
          audition {Math.min(seen, trials.length)} of {trials.length}
        </p>
        <p className="text-[13px] font-medium text-forest">
          “{cur.feature} ≤ {cur.threshold}?”
        </p>
        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <Bucket label="yes → left" s={cur.left} />
          <Bucket label="no → right" s={cur.right} />
        </div>
        <p className="mt-2 font-mono text-[11px] text-ink">
          gain = {cur.left.similarity} + {cur.right.similarity} − parent − {gamma} ={" "}
          <b className={cur.gain > 0 ? "text-green-700" : "text-red-600"}>{cur.gain}</b>
          {!cur.eligible && <span className="ml-1 text-red-600">(blocked: side too light)</span>}
        </p>
      </div>

      {/* the leaderboard */}
      <div className="rounded-lg border border-line bg-white p-2.5">
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-muted">
          leaderboard {done && "— winner crowned"}
        </p>
        <div className="space-y-1">
          {board.map(({ t, i }) => {
            const isWinner = done && t.kept;
            return (
              <div key={i} className="flex items-center gap-1.5">
                <span className="w-28 shrink-0 truncate text-[10px] text-ink">
                  {t.feature} ≤ {t.threshold}
                </span>
                <div className="h-3 flex-1 rounded bg-bg">
                  <div
                    className={`h-3 rounded transition-all duration-500 ${
                      isWinner ? "bg-[#C9A227]" : t.gain > 0 ? "bg-leaf/70" : "bg-red-300"
                    }`}
                    style={{ width: `${Math.min(100, (Math.max(0, t.gain) / maxGain) * 100)}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right font-mono text-[10px] text-muted">
                  {t.gain}
                </span>
                {isWinner && <span title="highest gain — kept">👑</span>}
              </div>
            );
          })}
        </div>
        {done && (
          <p className="mt-2 text-[10px] text-muted">
            The crowned split becomes this node's question; both sides now run their own
            auditions.
          </p>
        )}
      </div>
    </div>
  );
}

function Bucket({ label, s }: { label: string; s: SplitTrial["left"] }) {
  return (
    <div className="rounded border border-line bg-white px-2 py-1.5">
      <p className="text-[9px] uppercase tracking-wide text-muted">{label}</p>
      <p className="font-mono text-[10px] text-ink">
        {s.n} rows · Σg {s.sum_g} · Σh {s.sum_h}
      </p>
      <p className="font-mono text-[11px] font-semibold text-forest">sim {s.similarity}</p>
    </div>
  );
}

function findNode(root: XGBNode | null | undefined, id: string): XGBNode | null {
  if (!root) return null;
  if (root.id === id) return root;
  return findNode(root.left, id) ?? findNode(root.right, id);
}
