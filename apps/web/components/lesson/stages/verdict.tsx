"use client";

import type { LessonStageProps } from "./types";

/** The closing scene: pros / cons / limitations / when to prefer a named alternative. */
export default function VerdictStage({ lesson, step }: LessonStageProps) {
  const f = lesson.facts;
  if (!f)
    return (
      <p className="rounded-lg border border-line bg-white px-3 py-2 text-[12px] leading-relaxed text-ink">
        {step.narration}
      </p>
    );

  return (
    <div className="space-y-2">
      <div className="grid gap-1.5 sm:grid-cols-2">
        <FactList title="Strengths" icon="✓" tone="text-green-700" items={f.pros} />
        <FactList
          title="Weaknesses & limits"
          icon="✗"
          tone="text-red-600"
          items={[...f.cons, ...f.limitations]}
        />
      </div>
      {f.use_when.length > 0 && (
        <FactList title="Reach for it when" icon="→" tone="text-forest" items={f.use_when} />
      )}
      {f.alternatives.length > 0 && (
        <div className="rounded-lg border border-line bg-white px-2.5 py-2">
          <p className="mb-1 text-[11px] font-medium text-forest">Or pick an alternative…</p>
          <ul className="space-y-1">
            {f.alternatives.map((a) => (
              <li key={a.model} className="text-[11px] text-ink">
                <span className="font-medium text-[#8a6d1a]">{a.model}</span>{" "}
                <span className="text-muted">when {a.prefer_when}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="grid gap-1.5 sm:grid-cols-2">
        <FactList title="In the wild" icon="🏢" tone="text-forest" items={f.applications} />
        <FactList title="Edge cases & gotchas" icon="⚠" tone="text-[#8a6d1a]" items={f.edge_cases} />
      </div>
    </div>
  );
}

function FactList({
  title,
  icon,
  tone,
  items,
}: {
  title: string;
  icon: string;
  tone: string;
  items: string[];
}) {
  if (!items.length) return null;
  return (
    <div className="rounded-lg border border-line bg-white px-2.5 py-2">
      <p className="mb-1 text-[11px] font-medium text-forest">{title}</p>
      <ul className="space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex gap-1.5 text-[11px] text-ink">
            <span className={`shrink-0 font-semibold ${tone}`}>{icon}</span>
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}
