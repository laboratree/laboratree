"use client";

/** Side-by-side paper comparison — the library view that answers "which paper should I trust /
 *  reproduce?" in one screen: problem, data, models with their claimed numbers (each wearing its
 *  ✓ verified-in-paper receipt), best model, and results, aligned across papers. */

import type { EmpiricalCard, Paper } from "@/lib/api";
import { Verified } from "@/components/PaperCard";

function asEmpirical(p: Paper): EmpiricalCard | null {
  const c = p.card as EmpiricalCard;
  return c && c.paper_type === "empirical" ? c : null;
}

/** Pull the headline % from a claim string so the eye can compare instantly. */
function headlineNumber(text?: string): string | null {
  const m = (text ?? "").match(/(\d{2,3}(?:\.\d+)?)\s*%/);
  return m ? `${m[1]}%` : null;
}

function Cell({ children }: { children: React.ReactNode }) {
  return <td className="min-w-[16rem] max-w-[22rem] border-l border-line/60 px-3 py-2 align-top">{children}</td>;
}

function RowLabel({ children }: { children: React.ReactNode }) {
  return (
    <th className="sticky left-0 w-32 bg-bg px-3 py-2 text-left align-top text-[11px] font-medium uppercase tracking-wide text-muted">
      {children}
    </th>
  );
}

export default function PaperCompare({
  papers,
  onClose,
  onOpen,
}: {
  papers: Paper[];
  onClose: () => void;
  onOpen: (p: Paper) => void;
}) {
  const cols = papers.map((p) => ({ p, card: asEmpirical(p) }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={onClose} className="text-sm text-forest hover:underline">
          ← Back to papers
        </button>
        <h2 className="font-display text-xl text-forest">Compare papers</h2>
        <span className="text-xs text-muted">{papers.length} selected</span>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-line bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <RowLabel>Paper</RowLabel>
              {cols.map(({ p }) => (
                <Cell key={p.id}>
                  <button onClick={() => onOpen(p)} className="text-left font-medium text-forest hover:underline">
                    {p.title}
                  </button>
                  <p className="mt-0.5 text-[11px] text-muted">{p.status} · {p.n_chunks} chunks</p>
                </Cell>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            <tr>
              <RowLabel>Problem</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  <span className="text-ink">{card?.problem_statement?.one_liner || "—"}</span>
                </Cell>
              ))}
            </tr>
            <tr>
              <RowLabel>Predicts</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  {card ? (
                    <>
                      <span className="rounded-full bg-forest px-2 py-0.5 text-xs text-white">
                        {card.target_variable?.name || "—"}
                      </span>
                      <span className="ml-1.5 text-xs text-muted">
                        from {card.independent_variables?.length ?? 0} features
                      </span>
                    </>
                  ) : (
                    "—"
                  )}
                </Cell>
              ))}
            </tr>
            <tr>
              <RowLabel>Data</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  <span className="text-xs text-ink">{card?.data_sources?.join("; ") || "—"}</span>
                  {card?.data_sample && (
                    <p className="mt-0.5 text-[11px] text-muted">{card.data_sample.slice(0, 140)}</p>
                  )}
                </Cell>
              ))}
            </tr>
            <tr>
              <RowLabel>Models &amp; claims</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  {card?.models_used?.length ? (
                    <ul className="space-y-1.5">
                      {card.models_used.map((m, i) => {
                        const headline = headlineNumber(m.result);
                        return (
                          <li key={i} className="text-xs">
                            <span className="font-medium text-forest">{m.name}</span>
                            {headline && (
                              <span className="ml-1.5 rounded bg-leaf/15 px-1.5 py-0.5 font-semibold text-forest">
                                {headline}
                              </span>
                            )}
                            <Verified card={card} k={`model:${i}`} claim={m.result} />
                            {m.result && <p className="mt-0.5 text-muted">{m.result}</p>}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    "—"
                  )}
                </Cell>
              ))}
            </tr>
            <tr>
              <RowLabel>Best model</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  {card?.best_model ? (
                    <span className="text-xs text-ink">
                      🏆 {card.best_model}
                      <Verified card={card} k="best_model" claim={card.best_model} />
                    </span>
                  ) : (
                    "—"
                  )}
                </Cell>
              ))}
            </tr>
            <tr>
              <RowLabel>Results</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  <span className="text-xs text-ink">
                    {card?.results || "—"}
                    {card && <Verified card={card} k="results" claim={card.results} />}
                  </span>
                </Cell>
              ))}
            </tr>
            <tr>
              <RowLabel>Preprocessing</RowLabel>
              {cols.map(({ p, card }) => (
                <Cell key={p.id}>
                  {card?.preprocessing?.length ? (
                    <ul className="list-inside list-disc space-y-0.5 text-[11px] text-muted">
                      {card.preprocessing.slice(0, 5).map((s, i) => (
                        <li key={i}>{s.split("—")[0]}</li>
                      ))}
                    </ul>
                  ) : (
                    "—"
                  )}
                </Cell>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">
        ✓ badges = the claim's numbers were found verbatim in that paper&apos;s text (hover for the
        sentence). Open a paper to reproduce it in the Experiment Lab — running two papers against
        the same dataset is the real comparison.
      </p>
    </div>
  );
}
