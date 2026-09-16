"use client";

import { useEffect, useRef } from "react";

import { contourPaths, hashSeed } from "./texture.mjs";
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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    const paths = contourPaths({
      seed: String(hashSeed(seed)),
      width: size,
      height: size,
      cols: 18,
      rows: 18,
      levels: 7,
    });
    let raf = 0;
    const draw = () => {
      const target = state === "crisis" ? 0.08 : amplitude;
      lag.current += (target - lag.current) * (reduced ? 1 : 0.12);
      const scale =
        state === "thinking"
          ? 1 + Math.sin(performance.now() / 900) * 0.04
          : 1 + lag.current * 0.35 + breath * 0.08;
      ctx.clearRect(0, 0, size, size);
      ctx.save();
      ctx.translate(size / 2, size / 2);
      ctx.scale(scale, scale);
      if (state === "thinking" && !reduced) {
        ctx.rotate(performance.now() / 4000);
      }
      ctx.translate(-size / 2, -size / 2);
      ctx.strokeStyle = getComputedStyle(canvas).color;
      ctx.lineWidth = 1.25;
      ctx.globalAlpha = state === "crisis" ? 0.35 : 0.7;
      for (const path of paths) {
        const outline = new Path2D(path.d);
        ctx.stroke(outline);
      }
      if (state === "crisis") {
        ctx.globalAlpha = 0.5;
        for (let ring = 1; ring <= 4; ring += 1) {
          ctx.beginPath();
          ctx.arc(size / 2, size / 2, 18 * ring, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      ctx.restore();
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
