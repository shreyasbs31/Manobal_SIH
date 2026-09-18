"use client";

import { useEffect, useRef, useState } from "react";

import {
  BOX_BREATH_PATTERN,
  BREATH_SCALE_MAX,
  BREATH_SCALE_MIN,
  FOUR_SEVEN_EIGHT_PATTERN,
  MOTION,
  breathPhaseAt,
  breathScaleAt,
  motionToOpacityOnly,
} from "./motion-tokens.mjs";

export {
  BOX_BREATH_PATTERN,
  BREATH_SCALE_MAX,
  BREATH_SCALE_MIN,
  FOUR_SEVEN_EIGHT_PATTERN,
  MOTION,
  breathPhaseAt,
  breathScaleAt,
  motionToOpacityOnly,
};
export type MotionName = "instant" | "quick" | "settle" | "draw" | "breath";

export type BreathPhase = {
  id: string;
  label: string;
  ms: number;
  expand: boolean;
  hold: boolean;
  index: number;
  count: number;
};

export type BreathPattern = {
  id: string;
  label: string;
  ms: number;
  expand: boolean;
  hold: boolean;
}[];

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}

export function useBreath(active: boolean): number {
  const reduced = usePrefersReducedMotion();
  const [phase, setPhase] = useState(0);
  const origin = useRef<number | null>(null);
  useEffect(() => {
    if (!active || reduced) {
      origin.current = null;
      setPhase(0);
      return;
    }
    let raf = 0;
    const tick = (time: number) => {
      if (origin.current === null) {
        origin.current = time;
      }
      const elapsed = time - origin.current;
      setPhase((Math.sin((elapsed / MOTION.breath.duration) * Math.PI * 2) + 1) / 2);
      raf = window.requestAnimationFrame(tick);
    };
    raf = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(raf);
  }, [active, reduced]);
  return reduced ? 0.5 : phase;
}

const cycleOrigins = new Map<string, number>();

function patternKey(pattern: BreathPattern): string {
  return pattern.map((step) => `${step.id}:${step.ms}`).join("|");
}

export function breathOrigin(pattern: BreathPattern): number {
  const key = patternKey(pattern);
  const existing = cycleOrigins.get(key);
  if (existing !== undefined) {
    return existing;
  }
  const started = performance.now();
  cycleOrigins.set(key, started);
  return started;
}

export function useBreathCycle(pattern: BreathPattern = BOX_BREATH_PATTERN): BreathPhase {
  const reduced = usePrefersReducedMotion();
  const [phase, setPhase] = useState<BreathPhase>(() => breathPhaseAt(0, pattern) as BreathPhase);
  useEffect(() => {
    if (reduced) {
      setPhase(breathPhaseAt(0, pattern) as BreathPhase);
      return;
    }
    const started = breathOrigin(pattern);
    const tick = () => {
      setPhase(breathPhaseAt(performance.now() - started, pattern) as BreathPhase);
    };
    tick();
    const id = window.setInterval(tick, 200);
    return () => window.clearInterval(id);
  }, [pattern, reduced]);
  return phase;
}
