"use client";

import type { Lesson } from "@/lib/api";
import type { LessonClock } from "./clock";

/** Chapter stepper — numbered chips, done/current markers, click to jump. */
export default function ChapterNav({
  lesson,
  clock,
  currentChapter,
}: {
  lesson: Lesson;
  clock: LessonClock;
  currentChapter: number;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Chapters">
      {lesson.chapters.map((c, i) => {
        const state = i < currentChapter ? "done" : i === currentChapter ? "current" : "todo";
        return (
          <button
            key={c.id}
            role="tab"
            aria-selected={state === "current"}
            title={c.kicker || c.title}
            onClick={() => clock.jumpChapter(i)}
            className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
              state === "current"
                ? "border-forest bg-forest text-white"
                : state === "done"
                  ? "border-leaf/50 bg-leaf/10 text-forest"
                  : "border-line text-muted hover:text-forest"
            }`}
          >
            <span
              className={`font-mono text-[10px] ${state === "current" ? "text-white/80" : "text-muted"}`}
            >
              {state === "done" ? "✓" : String(i + 1).padStart(2, "0")}
            </span>
            {c.title}
          </button>
        );
      })}
    </div>
  );
}
