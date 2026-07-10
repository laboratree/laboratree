"use client";

/** PUBLIC read-only paper report — reachable by share link only (HMAC token), no login.
 *  Renders the verified Paper Card: problem, summary + per-model impact with ✓ receipts,
 *  variables, preprocessing funnel, results. */

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { API_URL, type EmpiricalCard, type PaperCardData } from "@/lib/api";
import { Verified } from "@/components/PaperCard";

type Shared = { title: string; filename: string; card: PaperCardData; created_at: string };

export default function SharedPaperPage() {
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const t = search.get("t") ?? "";
  const [data, setData] = useState<Shared | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id || !t) return;
    fetch(`${API_URL}/api/share/paper/${id}?t=${encodeURIComponent(t)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json())?.detail ?? "not found");
        setData(await r.json());
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "failed to load"));
  }, [id, t]);

  if (err)
    return (
      <main className="mx-auto max-w-2xl p-8 text-center">
        <p className="text-lg text-forest">This share link isn&apos;t valid.</p>
        <p className="mt-1 text-sm text-muted">{err}</p>
      </main>
    );
  if (!data)
    return <main className="mx-auto max-w-2xl p-8 text-center text-muted">Loading report…</main>;

  const card = data.card as EmpiricalCard;
  const empirical = card.paper_type === "empirical";

  return (
    <main className="mx-auto max-w-3xl space-y-4 p-6">
      <header className="rounded-2xl border border-line bg-white p-6">
        <p className="text-xs uppercase tracking-wide text-leaf">Laboratree · paper report</p>
        <h1 className="mt-1 font-display text-2xl text-forest">{data.title || data.filename}</h1>
        {empirical && card.problem_statement?.one_liner && (
          <p className="mt-2 font-medium text-ink">{card.problem_statement.one_liner}</p>
        )}
        {empirical && card.problem_statement?.plain && (
          <p className="mt-1 text-sm text-ink">{card.problem_statement.plain}</p>
        )}
      </header>

      {empirical ? (
        <>
          {card.detailed_summary && (
            <section className="rounded-2xl border border-line bg-white p-6">
              <h2 className="font-display text-lg text-forest">What the study did</h2>
              <p className="mt-1 text-sm text-ink">{card.detailed_summary}</p>
              {card.best_model && (
                <p className="mt-3 rounded-lg bg-leaf/10 p-3 text-sm text-forest">
                  🏆 <b>Best model:</b> {card.best_model}
                  <Verified card={card} k="best_model" claim={card.best_model} />
                </p>
              )}
            </section>
          )}

          {card.models_used?.some((m) => m.result) && (
            <section className="rounded-2xl border border-line bg-white p-6">
              <h2 className="font-display text-lg text-forest">How each model did</h2>
              <p className="mt-1 text-xs text-muted">
                ✓ badges link each claim to the exact sentence in the paper that supports it.
              </p>
              <ul className="mt-2 space-y-2 text-sm">
                {card.models_used.map((m, i) =>
                  m.result ? (
                    <li key={i}>
                      <span className="font-medium text-forest">{m.name}: </span>
                      <span className="text-ink">{m.result}</span>
                      <Verified card={card} k={`model:${i}`} claim={m.result} />
                    </li>
                  ) : null,
                )}
              </ul>
            </section>
          )}

          <section className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-line bg-white p-6">
              <h2 className="text-sm font-medium text-forest">Variables</h2>
              <p className="mt-1 text-xs text-muted">
                {card.independent_variables?.length ?? 0} features → predicts{" "}
                <b className="text-forest">{card.target_variable?.name || "—"}</b>
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {(card.independent_variables ?? []).slice(0, 30).map((v, i) => (
                  <span key={i} title={v.description} className="rounded-full bg-sprout/30 px-2 py-0.5 text-xs text-forest">
                    {v.name}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-line bg-white p-6">
              <h2 className="text-sm font-medium text-forest">Preprocessing funnel</h2>
              <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-ink">
                {(card.preprocessing ?? []).map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          </section>

          {card.results && (
            <section className="rounded-2xl border border-line bg-white p-6">
              <h2 className="font-display text-lg text-forest">Results</h2>
              <p className="mt-1 text-sm text-ink">
                {card.results}
                <Verified card={card} k="results" claim={card.results} />
              </p>
              {card.inference && <p className="mt-3 text-sm text-muted">{card.inference}</p>}
            </section>
          )}
        </>
      ) : (
        <section className="rounded-2xl border border-line bg-white p-6 text-sm text-ink">
          This is a conceptual paper — open it in Laboratree for the full segmented explainer.
        </section>
      )}

      <footer className="pb-6 text-center text-xs text-muted">
        Generated by <span className="font-medium text-forest">Laboratree</span> — the research lab
        that shows its work. Claims marked ✓ are grounded in the paper&apos;s own text.
      </footer>
    </main>
  );
}
