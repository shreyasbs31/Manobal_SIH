"use client";

import { useEffect, useState } from "react";

import { MOTION, motionToOpacityOnly } from "./motion-tokens.mjs";

export { MOTION, motionToOpacityOnly };
export type MotionName = "instant" | "quick" | "settle" | "draw" | "breath";

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
  useEffect(() => {
    if (!active || reduced) {
      setPhase(0);
      return;
    }
    let raf = 0;
    const tick = (time: number) => {
      setPhase((Math.sin((time / MOTION.breath.duration) * Math.PI * 2) + 1) / 2);
      raf = window.requestAnimationFrame(tick);
    };
    raf = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(raf);
  }, [active, reduced]);
  return reduced ? 0.5 : phase;
}
