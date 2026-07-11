import type { Lesson } from "@/lib/api";

/** Flattened playback timeline: one entry per lesson step, with cumulative times (ms at 1x). */
export type TimelineEntry = {
  start: number;
  end: number;
  chapterIdx: number;
  stepIdx: number;
  substeps: number; // micro-scrub granularity inside this step
};

export type Timeline = {
  entries: TimelineEntry[];
  total: number;
  chapterStart: number[]; // start time of each chapter (for jumps + scrubber ticks)
};

const MIN_STEP_MS = 1_000;
const DEFAULT_STEP_MS = 6_000;

export function buildTimeline(lesson: Lesson): Timeline {
  const entries: TimelineEntry[] = [];
  const chapterStart: number[] = [];
  let t = 0;
  lesson.chapters.forEach((c, chapterIdx) => {
    chapterStart.push(t);
    c.steps.forEach((s, stepIdx) => {
      const dur = Math.max(MIN_STEP_MS, s.duration_ms || DEFAULT_STEP_MS);
      entries.push({
        start: t,
        end: t + dur,
        chapterIdx,
        stepIdx,
        substeps: Math.max(1, s.anim?.substeps ?? 1),
      });
      t += dur;
    });
  });
  return { entries, total: t, chapterStart };
}

/** Index of the entry playing at time ``ms`` (clamped; binary search). */
export function entryAt(tl: Timeline, ms: number): number {
  const { entries } = tl;
  if (entries.length === 0) return 0;
  if (ms <= 0) return 0;
  if (ms >= tl.total) return entries.length - 1;
  let lo = 0;
  let hi = entries.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (entries[mid].end <= ms) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}
