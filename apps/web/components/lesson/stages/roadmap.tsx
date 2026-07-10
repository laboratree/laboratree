"use client";

import { useCallback } from "react";
import gsap from "gsap";
import { useStageTimeline } from "../useStageTimeline";
import type { LessonStageProps } from "./types";

/** The opening scene: chapter cards reveal one by one as the intro narration plays. */
export default function RoadmapStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const build = useCallback(
    (tl: gsap.core.Timeline, root: HTMLDivElement) => {
      const cards = root.querySelectorAll("[data-roadmap-card]");
      tl.fromTo(
        cards,
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, duration: 0.6, stagger: 0.5, ease: "power2.out" },
      );
    },
    [],
  );
  const ref = useStageTimeline(clock, entryIdx, build);

  return (
    <div ref={reducedMotion ? undefined : ref}>
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
        {lesson.chapters.map((c, i) => (
          <button
            key={c.id}
            data-roadmap-card
            onClick={() => clock.jumpChapter(i)}
            className="rounded-lg border border-line bg-white px-2.5 py-2 text-left transition hover:border-leaf/60"
            style={reducedMotion ? undefined : { opacity: 0 }}
          >
            <span className="font-mono text-[10px] text-muted">{String(i + 1).padStart(2, "0")}</span>
            <p className="text-[12px] font-medium text-forest">{c.title}</p>
            {c.kicker && <p className="mt-0.5 text-[10px] text-muted">{c.kicker}</p>}
          </button>
        ))}
      </div>
      <p className="mt-2 text-[10px] text-muted">
        ▶ plays automatically · space pauses · ← → step · click any chapter to jump
      </p>
    </div>
  );
}
