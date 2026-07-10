"use client";

import type { LessonMathBlock } from "@/lib/api";
import Tex from "@/components/Tex";

/** The step's math, broken all the way down: formula → plain words → each symbol → worked
 *  example with the live dataset's numbers. */
export default function MathPanel({ math }: { math: LessonMathBlock[] }) {
  if (!math.length) return null;
  return (
    <div className="space-y-2">
      {math.map((m, i) => (
        <div key={i} className="rounded-lg border border-line bg-white p-3">
          <p className="text-[11px] font-medium text-forest">{m.name}</p>
          <div className="my-1.5 overflow-x-auto">
            <Tex block className="text-[15px] text-ink">
              {m.formula}
            </Tex>
          </div>
          {m.plain && <p className="text-[12px] text-muted">{m.plain}</p>}
          {m.symbols.length > 0 && (
            <dl className="mt-2 space-y-0.5">
              {m.symbols.map((s) => (
                <div key={s.sym} className="flex gap-2 text-[11px]">
                  <dt className="w-14 shrink-0 font-mono text-forest">
                    <Tex>{s.sym}</Tex>
                  </dt>
                  <dd className="text-muted">{s.means}</dd>
                </div>
              ))}
            </dl>
          )}
          {m.worked && (
            <p className="mt-2 rounded border border-[#C9A227]/40 bg-[#FFFDF5] px-2 py-1.5 font-mono text-[11px] text-[#8a6d1a]">
              {m.worked}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
