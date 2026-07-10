import type { Lesson, LessonChapter, LessonStep } from "@/lib/api";
import type { LessonClock } from "../clock";

/** Contract every lesson stage implements — visuals derive everything from the clock, so
 *  play/pause/scrub/speed work identically across stages. */
export type LessonStageProps = {
  lesson: Lesson;
  chapter: LessonChapter;
  step: LessonStep;
  clock: LessonClock;
  entryIdx: number; // this step's index on the flattened timeline
  reducedMotion: boolean;
  hint?: string; // the paper's model name (variant cues, e.g. boosting mode)
};
