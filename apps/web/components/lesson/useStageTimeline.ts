"use client";

/**
 * Scrub a paused GSAP timeline from the lesson clock — the pattern every animated stage uses.
 *
 * The stage builds its tweens once into a PAUSED timeline; each clock frame sets
 * `tl.progress(p)` imperatively (zero React re-renders). Because nothing free-runs,
 * play/pause/seek/speed are exact, and stepping backwards replays perfectly.
 */

import { type RefObject, useEffect, useRef } from "react";
import gsap from "gsap";
import type { LessonClock } from "./clock";

export function useStageTimeline(
  clock: LessonClock,
  entryIdx: number,
  build: (tl: gsap.core.Timeline, root: HTMLDivElement) => void,
): RefObject<HTMLDivElement | null> {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const tl = gsap.timeline({ paused: true });
    const ctx = gsap.context(() => build(tl, el), el);
    const off = clock.onFrame((e, p) => {
      tl.progress(e < entryIdx ? 0 : e > entryIdx ? 1 : p);
    });
    return () => {
      off();
      tl.kill();
      ctx.revert();
    };
  }, [clock, entryIdx, build]);

  return ref;
}
