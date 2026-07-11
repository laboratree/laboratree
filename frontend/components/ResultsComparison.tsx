"use client";

/**
 * ResultsComparison — rich "paper vs ours" cards for the Experiment pipeline's
 * explanatory nodes:
 *   kind === "result"    → per-model comparison rows (paper claim vs our run)
 *   kind === "inference" → the authors' conclusion + does our re-run support it?
 *
 * Self-contained: fetches the Paper Card itself (like EdaPanel does) to get the
 * paper's per-model result strings; everything else arrives via props.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Api,
  type CardModel,
  type EmpiricalCard,
  type Experiment,
  type NodeRunResult,
  type WalkNode,
} from "@/lib/api";

/* ---------------- helpers ---------------- */

/** All percentages mentioned in a claim string, e.g. "99.1% accuracy" → [99.1]. */
function extractPcts(s: string | undefined | null): number[] {
  if (!s) return [];
  return Array.from(s.matchAll(/(\d+(?:\.\d+)?)\s*%/g))
    .map((m) => parseFloat(m[1]))
    .filter((v) => Number.isFinite(v) && v >= 0 && v <= 100);
}

/** Metrics that are 0–1 ratios and can be shown as a percentage next to paper claims. */
const RATIO_KEYS = new Set(["accuracy", "precision", "recall", "f1", "f1_macro", "roc_auc", "r2"]);

function toPct(key: string, value: number): number | null {
  if (!RATIO_KEYS.has(key) || !Number.isFinite(value)) return null;
  if (value >= 0 && value <= 1) return value * 100;
  if (value > 1 && value <= 100) return value; // already expressed as a percentage
  return null;
}

const fmtPct = (v: number) => {
  const s = v.toFixed(1);
  return s.endsWith(".0") ? s.slice(0, -2) : s;
};

/** Case-insensitive substring match (either direction) between a walkthrough node
 * title and a Paper-Card model name — "XGBoost" ↔ "XGBoost classifier". */
function titlesMatch(a: string, b: string): boolean {
  const na = a.toLowerCase().replace(/\s+/g, " ").trim();
  const nb = b.toLowerCase().replace(/\s+/g, " ").trim();
  return !!na && !!nb && (na.includes(nb) || nb.includes(na));
}

const GOLD = "#B8860B"; // paper claims (matches the "result" node accent)
const LEAF = "#6DB33F"; // our runs
const VIOLET = "#6C4FA1"; // inference accent

/* ---------------- tiny building blocks ---------------- */

/** Thin meter that animates its fill on mount (pure CSS transition). */
function Meter({ pct, color, delay = 0 }: { pct: number; color: string; delay?: number }) {
  const [w, setW] = useState(0);
  const target = Math.min(100, Math.max(2, pct)); // keep tiny values visible
  useEffect(() => {
    const t = setTimeout(() => setW(target), 80 + delay);
    return () => clearTimeout(t);
  }, [target, delay]);
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-bg">
      <div
        className="h-full rounded-full transition-[width] duration-700 ease-out"
        style={{ width: `${w}%`, background: color }}
      />
    </div>
  );
}

/** ▲ / ▼ / ≈ badge comparing our headline % to the paper's first claimed %. */
function DeltaBadge({ ours, paper }: { ours: number; paper: number }) {
  const d = ours - paper;
  if (Math.abs(d) <= 3) {
    return (
      <span className="shrink-0 rounded-full bg-leaf/15 px-2 py-0.5 text-[11px] font-semibold text-green-700">
        ≈ reproduces (±3 pts)
      </span>
    );
  }
  if (d > 0) {
    return (
      <span className="shrink-0 rounded-full bg-leaf/15 px-2 py-0.5 text-[11px] font-semibold text-green-700">
        ▲ +{fmtPct(d)} pts vs paper
      </span>
    );
  }
  return (
    <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
      ▼ {fmtPct(d)} pts vs paper
    </span>
  );
}

function MetricChips({ metrics }: { metrics: Record<string, number> }) {
  return (
    <div className="mt-1.5 flex flex-wrap gap-1">
      {Object.entries(metrics).map(([k, v]) => (
        <span key={k} className="rounded-full bg-bg px-2 py-0.5 text-[10px] text-muted">
          {k} <b className="font-semibold text-forest">{typeof v === "number" ? v.toFixed(3) : String(v)}</b>
        </span>
      ))}
    </div>
  );
}

/* ---------------- main component ---------------- */

type ComparisonRow = {
  id: string; // walkthrough node id (our run key)
  modelName: string; // the paper card's model name
  claim: string; // the paper's per-model result string
  paperPcts: number[];
  res: NodeRunResult;
  head: { key: string; value: number };
  oursPct: number | null;
};

export default function ResultsComparison({
  node,
  exp,
  results,
  primary,
}: {
  node: WalkNode;
  exp: Experiment;
  results: Record<string, NodeRunResult>;
  primary: (m: Record<string, number>) => { key: string; value: number };
}) {
  const [card, setCard] = useState<EmpiricalCard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    Api.getPaper(exp.paper_id)
      .then((p) => {
        if (!alive) return;
        const c = p.card as EmpiricalCard;
        if (c?.paper_type === "empirical") setCard(c);
      })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [exp.paper_id]);

  const synthetic = !!exp.fetch_report.fetched[0]?.synthetic;
  const nRuns = Object.keys(results).length;

  // one row per paper model that has BOTH a claim string and one of our runs
  const rows = useMemo<ComparisonRow[]>(() => {
    if (!card) return [];
    const used = new Set<string>();
    const out: ComparisonRow[] = [];
    for (const cm of card.models_used ?? []) {
      if (!cm?.name || !cm.result) continue;
      const match = exp.walkthrough.find(
        (n) => n.kind === "model" && !used.has(n.id) && !!results[n.id] && titlesMatch(n.title, cm.name),
      );
      if (!match) continue;
      used.add(match.id);
      const res = results[match.id];
      const head = primary(res.metrics);
      out.push({
        id: match.id,
        modelName: cm.name,
        claim: cm.result,
        paperPcts: extractPcts(cm.result),
        res,
        head,
        oursPct: toPct(head.key, head.value),
      });
    }
    return out;
  }, [card, exp.walkthrough, results, primary]);

  // paper models with a claim but no matching run yet (compact list, keeps the page honest)
  const unmatched = useMemo<CardModel[]>(
    () => (card?.models_used ?? []).filter((cm) => !!cm.result && !rows.some((r) => r.modelName === cm.name)),
    [card, rows],
  );

  // our overall best run (for the inference verdict)
  const best = useMemo(() => {
    let b: { id: string; res: NodeRunResult; head: { key: string; value: number } } | null = null;
    for (const [id, res] of Object.entries(results)) {
      const head = primary(res.metrics);
      if (!b || head.value > b.head.value) b = { id, res, head };
    }
    return b;
  }, [results, primary]);

  const bestTitle = best
    ? (exp.walkthrough.find((n) => n.id === best.id)?.title ??
      (best.res.component_id?.split(".").pop() ?? best.id).replace(/_/g, " "))
    : "";

  // first % the paper claims (results text → per-model claims → inference → node detail)
  const paperPct = useMemo(() => {
    const sources = [
      card?.results,
      ...(card?.models_used ?? []).map((m) => m.result),
      card?.inference,
      node.detail,
    ];
    for (const s of sources) {
      const p = extractPcts(s);
      if (p.length) return p[0];
    }
    return null;
  }, [card, node.detail]);

  if (loading && !card) {
    return (
      <p className="mt-3 text-sm text-muted">Loading the paper&apos;s reported numbers…</p>
    );
  }

  /* ---------- kind === "inference" ---------- */
  if (node.kind === "inference") {
    const conclusion = card?.inference || node.detail || "";
    const bestPct = best ? toPct(best.head.key, best.head.value) : null;
    const supports = bestPct != null && paperPct != null ? bestPct >= paperPct - 3 : null;
    return (
      <div className="mt-3 space-y-3 text-sm">
        {/* the authors' conclusion, as a quote card */}
        <blockquote
          className="rounded-2xl border border-line bg-white p-4"
          style={{ borderLeft: `4px solid ${VIOLET}` }}
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.09em]" style={{ color: VIOLET }}>
            💡 What the authors concluded
          </p>
          <p className="mt-1.5 font-display text-[15px] leading-relaxed text-forest">
            “{conclusion || "No conclusion text was extracted from this paper."}”
          </p>
        </blockquote>

        {/* does our re-run support it? */}
        <div className="rounded-2xl border border-line bg-white p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-muted">
            Does our re-run support it?
          </p>
          {best ? (
            <>
              <div className="mt-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <span className="font-display text-3xl font-semibold text-forest">
                  {bestPct != null ? `${fmtPct(bestPct)}%` : best.head.value.toFixed(3)}
                </span>
                <span className="text-xs text-muted">
                  {best.head.key} — our best run ({bestTitle})
                  {best.res.stand_in ? " · stand-in model" : ""}
                </span>
              </div>
              {bestPct != null && (
                <div className="mt-1.5">
                  <Meter pct={bestPct} color={LEAF} />
                </div>
              )}
              {supports === true && (
                <p className="mt-2 rounded-lg bg-leaf/10 p-2 text-xs text-green-700">
                  <b>✓ Our re-run supports this.</b> Our best headline ({fmtPct(bestPct!)}%) is within 3
                  points of — or above — the paper&apos;s claimed {fmtPct(paperPct!)}%, so the conclusion
                  holds on our run{synthetic ? " (on synthetic demo data — directionally, not exactly)" : ""}.
                </p>
              )}
              {supports === false && (
                <p className="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">
                  <b>▼ Not (yet) supported.</b> Our best headline ({fmtPct(bestPct!)}%) sits more than 3
                  points below the paper&apos;s claimed {fmtPct(paperPct!)}%.
                  {synthetic
                    ? " We ran on synthetic demo data, so a gap is expected — upload the paper's real dataset for a fair check."
                    : " Try the paper's exact preprocessing or another model before judging the claim."}
                </p>
              )}
              {supports === null && (
                <p className="mt-2 rounded-lg bg-bg p-2 text-xs text-muted">
                  The paper&apos;s conclusion doesn&apos;t state a percentage we can compare numerically —
                  judge it against our metrics above.
                </p>
              )}
            </>
          ) : (
            <p className="mt-2 rounded-lg bg-leaf/10 p-2.5 text-xs text-forest">
              No runs yet — run the <b>Model</b> steps (or <b>Run all</b> in Evaluation) and come back:
              we&apos;ll check your numbers against this conclusion automatically.
            </p>
          )}
        </div>
      </div>
    );
  }

  /* ---------- kind === "result" ---------- */
  return (
    <div className="mt-3 space-y-3 text-sm">
      {/* headline strip */}
      <div className="flex items-center justify-between gap-2 rounded-xl border border-line bg-gradient-to-r from-[#FBF3D6]/70 via-white to-leaf/10 px-3 py-2.5">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.09em]" style={{ color: "#8A6D1A" }}>
            📄 Paper reported
          </p>
          <p className="truncate text-[11px] text-muted">claims extracted from the paper</p>
        </div>
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-line bg-white text-[10px] font-bold text-forest shadow-sm">
          vs
        </span>
        <div className="min-w-0 text-right">
          <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-forest">What we got 🧪</p>
          <p className="truncate text-[11px] text-muted">
            {nRuns > 0 ? `${nRuns} run${nRuns === 1 ? "" : "s"} on this data` : "no runs yet"}
          </p>
        </div>
      </div>

      {/* per-model comparison rows */}
      {rows.length > 0 && (
        <ul className="space-y-2">
          {rows.map((r, i) => {
            const paperPick = !!card?.best_model && titlesMatch(card.best_model, r.modelName);
            return (
              <li key={r.id} className="rounded-2xl border border-line bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-1.5 font-medium text-forest">
                    <span className="truncate">{r.modelName}</span>
                    {paperPick && (
                      <span className="shrink-0 rounded-full bg-[#FBF3D6] px-1.5 py-0.5 text-[10px] font-semibold text-[#8A6D1A]">
                        paper&apos;s pick
                      </span>
                    )}
                  </span>
                  {r.oursPct != null && r.paperPcts.length > 0 ? (
                    <DeltaBadge ours={r.oursPct} paper={r.paperPcts[0]} />
                  ) : (
                    <span className="shrink-0 text-[10px] text-muted">no % to compare</span>
                  )}
                </div>

                <div className="mt-2 grid gap-3 sm:grid-cols-2">
                  {/* paper side */}
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.09em]" style={{ color: "#8A6D1A" }}>
                      Paper claims
                    </p>
                    {r.paperPcts.length > 0 ? (
                      <p className="mt-0.5 flex flex-wrap items-baseline gap-x-1.5">
                        {r.paperPcts.slice(0, 3).map((p, j) => (
                          <span key={j} className="whitespace-nowrap">
                            <span className="font-display text-2xl font-semibold text-forest">{fmtPct(p)}</span>
                            <span className="text-xs text-muted">%</span>
                            {j < Math.min(r.paperPcts.length, 3) - 1 && (
                              <span className="text-muted"> · </span>
                            )}
                          </span>
                        ))}
                      </p>
                    ) : (
                      <p className="mt-0.5 text-xs italic text-muted">no number stated</p>
                    )}
                    {r.paperPcts.length > 0 && (
                      <div className="mt-1.5">
                        <Meter pct={r.paperPcts[0]} color={GOLD} delay={i * 90} />
                      </div>
                    )}
                    <p className="mt-1.5 text-[11px] italic leading-snug text-muted">“{r.claim}”</p>
                  </div>

                  {/* our side */}
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-forest">
                      Ours · {r.head.key}
                      {r.res.stand_in ? (
                        <span className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[9px] font-semibold normal-case tracking-normal text-amber-800">
                          stand-in
                        </span>
                      ) : null}
                    </p>
                    <p className="mt-0.5">
                      <span className="font-display text-2xl font-semibold text-forest">
                        {r.oursPct != null ? fmtPct(r.oursPct) : r.head.value.toFixed(3)}
                      </span>
                      {r.oursPct != null && <span className="text-xs text-muted">%</span>}
                    </p>
                    {r.oursPct != null && (
                      <div className="mt-1.5">
                        <Meter pct={r.oursPct} color={LEAF} delay={i * 90 + 140} />
                      </div>
                    )}
                    <MetricChips metrics={r.res.metrics} />
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* claims we can't compare yet (no matching run) */}
      {unmatched.length > 0 && (
        <div className="rounded-xl border border-dashed border-line bg-white p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-muted">
            {rows.length > 0 ? "Also reported in the paper — not run yet" : "Reported in the paper — run the models to compare"}
          </p>
          <ul className="mt-1.5 space-y-1">
            {unmatched.map((cm) => (
              <li key={cm.name} className="text-[11px] leading-snug">
                <span className="font-medium text-forest">{cm.name}</span>{" "}
                <span className="italic text-muted">— “{cm.result}”</span>
              </li>
            ))}
          </ul>
          {nRuns === 0 && (
            <p className="mt-2 text-[11px] text-muted">
              Run the <b className="text-forest">Model</b> steps (or <b className="text-forest">Run all</b>{" "}
              in Evaluation) to see your numbers side-by-side here.
            </p>
          )}
        </div>
      )}

      {/* no structured claims at all — fall back gracefully */}
      {!card && (
        <p className="rounded-lg bg-bg p-2.5 text-xs text-muted">
          No structured per-model claims could be loaded from the Paper Card for this paper.
        </p>
      )}

      {/* synthetic-data caveat */}
      {synthetic && (
        <p className="rounded-lg bg-amber-50 p-2.5 text-xs text-amber-800">
          ⚠ These runs used <b>synthetic demo data</b>, so absolute numbers won&apos;t match the paper —
          the comparison shows whether the pipeline behaves the same way, not the exact figures.
        </p>
      )}

      {/* the paper's overall results text, as a quiet quote */}
      {(card?.results || node.detail) && (
        <blockquote className="rounded-xl bg-bg p-3" style={{ borderLeft: `3px solid ${GOLD}` }}>
          <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-muted">
            From the paper — reported results
          </p>
          <p className="mt-1 text-xs leading-relaxed text-ink">“{card?.results || node.detail}”</p>
        </blockquote>
      )}
    </div>
  );
}
