"use client";

import { useEffect, useRef } from "react";

import { hashSeed } from "./texture.mjs";
import { useBreath, usePrefersReducedMotion } from "./motion";

export type VoiceState = "idle" | "listening" | "thinking" | "speaking" | "crisis";

export function VoiceContour({
  state = "listening",
  amplitude = 0.35,
  seed = "MB-4091",
  size = 260,
}: {
  state?: VoiceState | undefined;
  amplitude?: number | undefined;
  seed?: string | undefined;
  size?: number | undefined;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const reduced = usePrefersReducedMotion();
  const breath = useBreath(state === "speaking" || state === "listening");
  const lag = useRef(amplitude);
  const phase = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    const noiseSeed = hashSeed(seed);
    let raf = 0;
    const draw = () => {
      const target = state === "crisis" ? 0.04 : amplitude;
      lag.current += (target - lag.current) * (reduced ? 1 : 0.12);
      if (state === "thinking" && !reduced) {
        phase.current += 0.012;
      }
      ctx.clearRect(0, 0, size, size);
      ctx.strokeStyle = getComputedStyle(canvas).color;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = "round";
      const rings = state === "crisis" ? 4 : 7;
      for (let ring = 1; ring <= rings; ring += 1) {
        ctx.beginPath();
        ctx.globalAlpha = 0.35 + ring / 16;
        const base = (size / 2 - 16) * (ring / rings);
        const jitter = state === "crisis" ? 0 : 5 + lag.current * 18 + breath * 6;
        for (let step = 0; step <= 72; step += 1) {
          const angle = (step / 72) * Math.PI * 2 + (state === "thinking" ? phase.current : 0);
          const wobble =
            Math.sin(angle * 3 + ring + noiseSeed) * jitter * 0.35 +
            Math.sin(angle * 5 - ring * 0.7) * jitter * 0.2;
          const radius = base + wobble;
          const x = size / 2 + Math.cos(angle) * radius;
          const y = size / 2 + Math.sin(angle) * radius;
          if (step === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.closePath();
        ctx.stroke();
      }
      raf = window.requestAnimationFrame(draw);
    };
    raf = window.requestAnimationFrame(draw);
    return () => window.cancelAnimationFrame(raf);
  }, [amplitude, breath, reduced, seed, size, state]);

  return (
    <canvas
      aria-label={`Saathi voice, ${state}`}
      className="mb-voice-contour"
      height={size}
      ref={canvasRef}
      role="img"
      width={size}
    />
  );
}
