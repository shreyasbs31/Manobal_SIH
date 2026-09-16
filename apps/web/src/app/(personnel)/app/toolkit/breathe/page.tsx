"use client";

import { breathPulse, useBreath, usePrefersReducedMotion } from "@manobal/ui";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

export default function BreathePage() {
  const breath = useBreath(true);
  const reduced = usePrefersReducedMotion();
  const inhale = breath >= 0.5;
  const [count, setCount] = useState(4);
  const last = useRef(inhale);

  useEffect(() => {
    if (last.current === inhale) {
      return;
    }
    last.current = inhale;
    setCount(4);
    breathPulse();
  }, [inhale]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCount((value) => (value <= 1 ? 4 : value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [inhale]);

  const scale = reduced ? 1 : 0.86 + breath * 0.24;

  return (
    <div className="mb-breathe">
      <Link className="mb-ghost mb-breathe-exit" href="/app/toolkit">
        Exit
      </Link>
      <div className="mb-breath-ring" style={{ borderColor: "var(--neem)", transform: `scale(${scale})` }} />
      <p className="mb-breathe-count">{count}</p>
      <p>{inhale ? "Breathe in" : "Breathe out"}</p>
    </div>
  );
}
