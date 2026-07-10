"use client";

/**
 * The cinematic lesson player — plays a backend `Lesson` like a documentary.
 *
 * One master clock (single RAF) drives everything: the chapter nav, the active stage, the
 * caption, and the transport. Stages are pure functions of (step, progress), so
 * pause/scrub/speed/step are exact. All data arrives in the one lesson payload — zero
 * network requests during playback.
 */

import { useMemo, type KeyboardEvent } from "react";
import type { Lesson } from "@/lib/api";
import CaptionBar from "./CaptionBar";
import ChapterNav from "./ChapterNav";
import { useLessonClock, useReducedMotion } from "./clock";
import MathPanel from "./MathPanel";
import { stageFor } from "./StageRouter";
import { buildTimeline } from "./timeline";
import Transport from "./Transport";
import { useSyncExternalStore } from "react";

export default function LessonPlayer({
  lesson,
  hint,
  theater = false,
}: {
  lesson: Lesson;
  hint?: string;
  theater?: boolean; // Learning Lab full-width mode
}) {
  const timeline = useMemo(() => buildTimeline(lesson), [lesson]);
  const reducedMotion = useReducedMotion();
  const clock = useLessonClock(timeline, !reducedMotion);
  const snap = useSyncExternalStore(clock.subscribe, clock.getSnapshot, clock.getSnapshot);

  const entryIdx = Math.min(snap.entryIdx, Math.max(0, timeline.entries.length - 1));
  const entry = timeline.entries[entryIdx];
  if (!entry) return null;
  const chapter = lesson.chapters[entry.chapterIdx];
  const step = chapter.steps[entry.stepIdx];
  const Stage = stageFor(step.anim?.kind);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === " ") {
      e.preventDefault();
      clock.toggle();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      clock.stepForward();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      clock.stepBack();
    }
  };

  return (
    <div
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="space-y-2 rounded-xl outline-none focus-visible:ring-1 focus-visible:ring-leaf/60"
      aria-label={`${lesson.title} guided lesson`}
    >
      {/* the marquee: what's showing, and where we are in the programme */}
      <div className="flex items-baseline justify-between gap-3 rounded-xl bg-forest px-3.5 py-2 text-white">
        <div className="min-w-0">
          <p className="truncate font-display text-[15px]">{lesson.title}</p>
          <p className="truncate text-[10px] uppercase tracking-widest text-[#E9CF7A]">
            {chapter.title}
          </p>
        </div>
        <p className="shrink-0 font-mono text-[10px] text-white/60">
          chapter {entry.chapterIdx + 1} / {lesson.chapters.length}
        </p>
      </div>

      <ChapterNav lesson={lesson} clock={clock} currentChapter={entry.chapterIdx} />

      {/* the screen */}
      <div
        className={`rounded-xl border border-line bg-white p-3 shadow-[inset_0_1px_6px_rgba(20,52,42,0.05)] ${theater ? "min-h-[340px]" : "min-h-[240px]"}`}
      >
        <Stage
          key={`${entry.chapterIdx}-${entry.stepIdx}`}
          lesson={lesson}
          chapter={chapter}
          step={step}
          clock={clock}
          entryIdx={entryIdx}
          reducedMotion={reducedMotion}
          hint={hint}
        />
      </div>

      {step.anim?.kind !== "note" && (
        <CaptionBar chapter={chapter} step={step} stepKey={`${entry.chapterIdx}-${entry.stepIdx}`} />
      )}
      {step.math.length > 0 && <MathPanel math={step.math} />}
      <Transport clock={clock} lesson={lesson} timeline={timeline} />
      {snap.ended && (
        <p className="text-center text-[11px] text-muted">
          The show is over — press ▶ to replay, or jump to any chapter above.
        </p>
      )}
    </div>
  );
}
