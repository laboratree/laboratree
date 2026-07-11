"use client";

/**
 * The lesson master clock — ONE requestAnimationFrame loop drives the whole show.
 *
 * Two subscription lanes keep playback buttery:
 *  - coarse (useSyncExternalStore): step index / playing / speed / ended — React re-renders
 *    only when one of those changes (a few times a minute).
 *  - fine (onFrame): per-frame (entry, progress 0..1) callbacks for the active stage and the
 *    scrubber — no React involvement unless the subscriber opts in.
 *
 * Speed multiplies the frame delta; seeking/stepping/jumping just move `t`. Stages are pure
 * functions of (step, progress), so pause/scrub/speed are exact by construction.
 */

import { useEffect, useMemo, useState } from "react";
import { type Timeline, entryAt } from "./timeline";

export type Speed = 0.5 | 1 | 2;
export const SPEEDS: Speed[] = [0.5, 1, 2];

export type ClockSnapshot = {
  entryIdx: number;
  playing: boolean;
  speed: Speed;
  ended: boolean;
};

export type FrameListener = (entryIdx: number, progress: number, timeMs: number) => void;

export class LessonClock {
  readonly timeline: Timeline;
  private t = 0;
  private playing = false;
  private speed: Speed = 1;
  private ended = false;
  private raf = 0;
  private last = 0;
  private snapshot: ClockSnapshot;
  private coarse = new Set<() => void>();
  private frame = new Set<FrameListener>();

  constructor(timeline: Timeline) {
    this.timeline = timeline;
    this.snapshot = { entryIdx: 0, playing: false, speed: 1, ended: false };
  }

  /* ---- subscriptions -------------------------------------------------- */

  subscribe = (cb: () => void): (() => void) => {
    this.coarse.add(cb);
    return () => this.coarse.delete(cb);
  };

  getSnapshot = (): ClockSnapshot => this.snapshot;

  /** Fires immediately with the current position, then on every frame/seek. */
  onFrame = (cb: FrameListener): (() => void) => {
    this.frame.add(cb);
    const e = entryAt(this.timeline, this.t);
    cb(e, this.progressIn(e), this.t);
    return () => this.frame.delete(cb);
  };

  /* ---- transport actions ---------------------------------------------- */

  play = (): void => {
    if (this.playing) return;
    if (this.ended || this.t >= this.timeline.total) this.t = 0; // replay from the top
    this.playing = true;
    this.ended = false;
    this.last = performance.now();
    this.raf = requestAnimationFrame(this.tick);
    this.emit();
  };

  pause = (): void => {
    if (!this.playing) return;
    this.playing = false;
    cancelAnimationFrame(this.raf);
    this.emit();
  };

  toggle = (): void => (this.playing ? this.pause() : this.play());

  seek = (ms: number): void => {
    this.t = Math.max(0, Math.min(this.timeline.total, ms));
    this.ended = this.t >= this.timeline.total;
    if (this.ended) this.pause();
    this.emit();
  };

  /** Jump to the start of the next step and pause, so the viewer can read at their own pace. */
  stepForward = (): void => {
    const i = entryAt(this.timeline, this.t);
    const next = this.timeline.entries[i + 1];
    this.pause();
    this.seek(next ? next.start : this.timeline.total);
  };

  stepBack = (): void => {
    const i = entryAt(this.timeline, this.t);
    const cur = this.timeline.entries[i];
    // within the first moments of a step, "back" means the previous step
    const target =
      cur && this.t - cur.start > 800 ? cur.start : (this.timeline.entries[i - 1]?.start ?? 0);
    this.pause();
    this.seek(target);
  };

  jumpChapter = (chapterIdx: number): void => {
    const start = this.timeline.chapterStart[chapterIdx];
    if (start != null) this.seek(start);
  };

  setSpeed = (s: Speed): void => {
    this.speed = s;
    this.emit();
  };

  get time(): number {
    return this.t;
  }

  dispose = (): void => {
    cancelAnimationFrame(this.raf);
    this.playing = false;
    this.coarse.clear();
    this.frame.clear();
  };

  /* ---- internals -------------------------------------------------------- */

  private tick = (now: number): void => {
    if (!this.playing) return;
    const dt = now - this.last;
    this.last = now;
    this.t = Math.min(this.timeline.total, this.t + dt * this.speed);
    if (this.t >= this.timeline.total) {
      this.playing = false;
      this.ended = true;
    } else {
      this.raf = requestAnimationFrame(this.tick);
    }
    this.emit();
  };

  private progressIn(entryIdx: number): number {
    const e = this.timeline.entries[entryIdx];
    if (!e || e.end <= e.start) return 0;
    return Math.max(0, Math.min(1, (this.t - e.start) / (e.end - e.start)));
  }

  private emit(): void {
    const entryIdx = entryAt(this.timeline, this.t);
    const progress = this.progressIn(entryIdx);
    for (const cb of this.frame) cb(entryIdx, progress, this.t);
    const s = this.snapshot;
    if (
      s.entryIdx !== entryIdx ||
      s.playing !== this.playing ||
      s.speed !== this.speed ||
      s.ended !== this.ended
    ) {
      this.snapshot = { entryIdx, playing: this.playing, speed: this.speed, ended: this.ended };
      for (const cb of this.coarse) cb();
    }
  }
}

/* ---- hooks ---------------------------------------------------------------- */

/** Create (and dispose) a clock for a timeline; optionally start playing on mount. */
export function useLessonClock(timeline: Timeline, autoplay: boolean): LessonClock {
  const clock = useMemo(() => new LessonClock(timeline), [timeline]);
  useEffect(() => {
    if (autoplay) clock.play();
    return () => clock.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clock]);
  return clock;
}

/**
 * Discrete micro-step (1..substeps) inside one timeline entry — re-renders the caller ONLY
 * when the integer changes. 0 before the step is reached; `substeps` once it has passed.
 */
export function useSubstep(clock: LessonClock, entryIdx: number, substeps: number): number {
  const [sub, setSub] = useState(0);
  useEffect(() => {
    return clock.onFrame((e, p) => {
      const v =
        e < entryIdx ? 0 : e > entryIdx ? substeps : Math.min(substeps, Math.floor(p * substeps) + 1);
      setSub((prev) => (prev === v ? prev : v));
    });
  }, [clock, entryIdx, substeps]);
  return sub;
}

/**
 * Continuous progress (0..1) inside one timeline entry — re-renders the caller per frame.
 * Only for SMALL subtrees (a widget's SVG marker); larger stages should quantize (useSubstep)
 * or scrub a GSAP timeline (useStageTimeline) instead.
 */
export function useSmoothProgress(clock: LessonClock, entryIdx: number): number {
  const [p, setP] = useState(0);
  useEffect(() => {
    return clock.onFrame((e, prog) => {
      const v = e < entryIdx ? 0 : e > entryIdx ? 1 : prog;
      setP((prev) => (Math.abs(prev - v) < 0.002 ? prev : v));
    });
  }, [clock, entryIdx]);
  return p;
}

/** Honor the OS "reduce motion" preference: no autoplay, instant transitions. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const on = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}
