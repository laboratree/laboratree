"use client";

import { useState } from "react";
import { stagesFor } from "@/components/model-viz";
import { TestTable } from "@/components/model-viz/test-table";
import type { LessonStageProps } from "./types";

/** Adapter: the held-out results table + per-row walkthrough inside a lesson chapter. */
export default function LegacyTestStage({ lesson, hint }: LessonStageProps) {
  const [rowIdx, setRowIdx] = useState(0);
  const { Test } = stagesFor(lesson.family);
  const rows = lesson.trace.test_rows ?? [];
  if (!rows.length) return <p className="text-xs text-muted">No held-out rows to test on.</p>;
  return (
    <TestTable
      trace={lesson.trace}
      rows={rows}
      rowIdx={rowIdx}
      setRowIdx={setRowIdx}
      Test={Test}
      hint={hint}
    />
  );
}
