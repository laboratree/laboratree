"use client";

import type { LessonStageProps } from "./types";

/** A "key idea" scene — the narration IS the stage (the caption bar hides for kind "note"). */
export default function NoteStage({ chapter, step }: LessonStageProps) {
  return (
    <div className="flex min-h-[200px] items-center justify-center px-2 py-4">
      <div className="max-w-xl text-center">
        {chapter.kicker && (
          <p className="mb-2 text-[10px] font-medium uppercase tracking-widest text-[#8a6d1a]">
            {chapter.kicker}
          </p>
        )}
        <p className="font-display text-[17px] leading-relaxed text-forest">{step.narration}</p>
      </div>
    </div>
  );
}
