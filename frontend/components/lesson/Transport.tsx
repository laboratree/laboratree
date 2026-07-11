"use client";

import { useEffect, useState } from "react";
import type { Lesson } from "@/lib/api";
import { type LessonClock, SPEEDS, useReducedMotion } from "./clock";
import type { Timeline } from "./timeline";

/** The player bar — deliberately dark, like a cinema transport: it tells you this PLAYS.
 *  Play/pause · step ◀ ▶ · scrubber with chapter ticks · time · speed. */
export default function Transport({
  clock,
  lesson,
  timeline,
}: {
  clock: LessonClock;
  lesson: Lesson;
  timeline: Timeline;
}) {
  const reduced = useReducedMotion();
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(clock.getSnapshot().speed);

  useEffect(() => {
    const offFrame = clock.onFrame((_e, _p, t) => setTime(t));
    const offCoarse = clock.subscribe(() => {
      const s = clock.getSnapshot();
      setPlaying(s.playing);
      setSpeed(s.speed);
    });
    return () => {
      offFrame();
      offCoarse();
    };
  }, [clock]);

  const nextSpeed = () => {
    const i = SPEEDS.indexOf(speed);
    clock.setSpeed(SPEEDS[(i + 1) % SPEEDS.length]);
  };

  return (
    <div className="flex items-center gap-2 rounded-xl bg-forest px-2.5 py-2 text-white shadow-sm">
      <button
        onClick={clock.stepBack}
        title="Previous step (←)"
        className="rounded px-1.5 py-0.5 text-sm text-white/70 transition hover:text-white focus-visible:outline focus-visible:outline-1 focus-visible:outline-[#C9A227]"
      >
        ⏮
      </button>
      <button
        onClick={clock.toggle}
        title="Play / pause (space)"
        className="grid h-8 w-8 place-items-center rounded-full bg-[#C9A227] text-sm font-semibold text-forest transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
      >
        {playing ? "❚❚" : "▶"}
      </button>
      <button
        onClick={clock.stepForward}
        title="Next step (→)"
        className="rounded px-1.5 py-0.5 text-sm text-white/70 transition hover:text-white focus-visible:outline focus-visible:outline-1 focus-visible:outline-[#C9A227]"
      >
        ⏭
      </button>

      <div className="relative min-w-0 flex-1">
        {/* chapter tick marks over the scrubber track */}
        {timeline.chapterStart.slice(1).map((start, i) => (
          <span
            key={i}
            title={lesson.chapters[i + 1]?.title}
            className="pointer-events-none absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-white/30"
            style={{ left: `${(start / Math.max(1, timeline.total)) * 100}%` }}
          />
        ))}
        <input
          type="range"
          min={0}
          max={Math.max(1, timeline.total)}
          step={100}
          value={Math.round(time)}
          onChange={(e) => clock.seek(Number(e.target.value))}
          className="w-full accent-[#C9A227]"
          aria-label="Lesson position"
        />
      </div>

      <span className="whitespace-nowrap font-mono text-[10px] text-white/70">
        {fmt(time)} / {fmt(timeline.total)}
      </span>
      <button
        onClick={nextSpeed}
        title="Playback speed"
        className={`rounded-full border px-2 py-0.5 text-[11px] font-medium transition focus-visible:outline focus-visible:outline-1 focus-visible:outline-[#C9A227] ${
          speed !== 1
            ? "border-[#C9A227] text-[#E9CF7A]"
            : "border-white/30 text-white/80 hover:border-white/60"
        }`}
      >
        {speed}×
      </button>
      {reduced && (
        <span className="text-[10px] text-white/60" title="OS reduced-motion is on; autoplay is off">
          step-through
        </span>
      )}
    </div>
  );
}

function fmt(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
