"use client";

import { useState } from "react";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** Self-check flip-cards: think first, click to reveal the model answer. Cards surface one by
 *  one under the clock so the autoplay show ends with a guided drill. */
export default function QuizStage({ step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const qa = step.quiz;
  const shown = useSubstep(clock, entryIdx, Math.max(1, qa.length));
  const visible = reducedMotion ? qa.length : shown;
  const [open, setOpen] = useState<Set<number>>(new Set());
  if (!qa.length) return <p className="text-xs text-muted">No self-check questions yet.</p>;

  const toggle = (i: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div className="space-y-1.5">
      {qa.map((item, i) => {
        const revealed = open.has(i);
        return (
          <button
            key={i}
            onClick={() => toggle(i)}
            className={`block w-full rounded-lg border p-2.5 text-left transition ${
              revealed ? "border-leaf/60 bg-[#F6FAF2]" : "border-line bg-white hover:border-[#C9A227]/60"
            }`}
            style={{
              opacity: i < visible ? 1 : 0,
              transform: i < visible ? "none" : "translateY(6px)",
              transition: reducedMotion ? undefined : "opacity .4s ease, transform .4s ease",
            }}
          >
            <p className="text-[12px] font-medium text-forest">
              <span className="mr-1.5 font-mono text-[10px] text-muted">Q{i + 1}</span>
              {item.q}
            </p>
            {revealed ? (
              <p className="mt-1.5 border-t border-line/60 pt-1.5 text-[11px] leading-relaxed text-ink">
                {item.a}
              </p>
            ) : (
              <p className="mt-1 text-[10px] text-[#8a6d1a]">think first — click to reveal</p>
            )}
          </button>
        );
      })}
    </div>
  );
}
