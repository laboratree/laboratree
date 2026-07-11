"use client";

import { useSmoothProgress } from "../clock";
import { WIDGETS } from "../widgets";
import type { LessonStageProps } from "./types";

/** Renders the step's concept widget (gini balls, hessian bowl, …) scrubbed by the clock. */
export default function WidgetStage({ step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const progress = useSmoothProgress(clock, entryIdx);
  const Widget = step.widget ? WIDGETS[step.widget] : undefined;
  if (!Widget)
    return <p className="text-xs text-muted">({step.widget ?? "concept"} illustration)</p>;
  return (
    <div className="mx-auto max-w-md">
      <Widget progress={reducedMotion ? 1 : progress} reducedMotion={reducedMotion} />
    </div>
  );
}
