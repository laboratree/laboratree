"use client";

import type { LessonChapter, LessonStep } from "@/lib/api";

/** The narration caption for the current step — cross-fades on step change. */
export default function CaptionBar({
  chapter,
  step,
  stepKey,
}: {
  chapter: LessonChapter;
  step: LessonStep;
  stepKey: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-gradient-to-b from-white to-[#F6FAF2] px-3 py-2">
      <style>{`@keyframes lessonCaptionIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }`}</style>
      <div key={stepKey} style={{ animation: "lessonCaptionIn .4s ease-out both" }}>
        {chapter.kicker && (
          <p className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
            {chapter.kicker}
          </p>
        )}
        <p className="text-[13px] leading-relaxed text-ink">{step.narration}</p>
      </div>
    </div>
  );
}
