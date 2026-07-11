"use client";

import { stagesFor } from "@/components/model-viz";
import type { LessonStageProps } from "./types";

/** Adapter: the family's existing (self-driven) training animation inside a lesson chapter.
 *  Replaced by clock-driven stages as deep lessons roll out per family. */
export default function LegacyTrainStage({ lesson, hint }: LessonStageProps) {
  const { Train } = stagesFor(lesson.family);
  return <Train trace={lesson.trace} hint={hint} />;
}
