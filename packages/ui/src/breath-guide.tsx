"use client";

import { useLayoutEffect, useRef, useState } from "react";

import {
  BOX_BREATH_PATTERN,
  type BreathPattern,
  type BreathPhase,
  breathOrigin,
  breathPhaseAt,
  breathScaleAt,
  usePrefersReducedMotion,
} from "./motion";
import { breathPulse } from "./sound";

export function BreathGuide({
  pattern = BOX_BREATH_PATTERN,
  title,
}: {
  pattern?: BreathPattern;
  title: string;
}) {
  const reduced = usePrefersReducedMotion();
  const ringRef = useRef<HTMLDivElement>(null);
  const lastId = useRef<string | null>(null);
  const [phase, setPhase] = useState<BreathPhase>(
    () => breathPhaseAt(0, pattern) as BreathPhase,
  );

  useLayoutEffect(() => {
    const page = ringRef.current?.closest(".mb-breathe") as HTMLElement | null;
    const fit = () => {
      if (!page) {
        return;
      }
      page.style.minHeight = `${window.innerHeight}px`;
      page.style.height = `${window.innerHeight}px`;
    };
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  useLayoutEffect(() => {
    const ring = ringRef.current;
    if (reduced) {
      if (ring) {
        ring.style.transform = "scale(1)";
      }
      setPhase(breathPhaseAt(0, pattern) as BreathPhase);
      return;
    }
    const started = breathOrigin(pattern);
    const tick = () => {
      const elapsed = performance.now() - started;
      const next = breathPhaseAt(elapsed, pattern) as BreathPhase;
      if (ring) {
        ring.style.transform = `scale(${breathScaleAt(elapsed, pattern).toFixed(4)})`;
      }
      setPhase((prev) =>
        prev.id === next.id && prev.count === next.count ? prev : next,
      );
      if (lastId.current !== next.id) {
        const first = lastId.current === null;
        lastId.current = next.id;
        if (!first || !next.hold) {
          breathPulse();
        }
      }
    };
    tick();
    const id = window.setInterval(tick, 50);
    return () => window.clearInterval(id);
  }, [pattern, reduced]);

  return (
    <div className="mb-breathe-inner">
      <div
        ref={ringRef}
        aria-hidden="true"
        className="mb-breath-ring"
        data-pattern={pattern.length === 3 ? "478" : "box"}
      />
      <p className="mb-breathe-count">{reduced ? "" : phase.count}</p>
      <p className="mb-breathe-phase" aria-live="polite">
        {reduced ? title : phase.label}
      </p>
    </div>
  );
}
