"use client";

import { useMemo } from "react";

import { contourPaths } from "./texture.mjs";

export function ContourTexture({
  seed,
  width = 390,
  height = 220,
  opacity = 0.45,
}: {
  seed: string;
  width?: number | undefined;
  height?: number | undefined;
  opacity?: number | undefined;
}) {
  const paths = useMemo(
    () => contourPaths({ seed, width, height }),
    [seed, width, height],
  );
  return (
    <svg
      aria-hidden="true"
      className="mb-contour-texture"
      preserveAspectRatio="none"
      style={{ opacity }}
      viewBox={`0 0 ${width} ${height}`}
    >
      {paths.map((path: { d: string; level: number }) => (
        <path d={path.d} key={path.level} />
      ))}
    </svg>
  );
}

export function MapGrid({
  refs = false,
  columns = 12,
  rows = 6,
}: {
  refs?: boolean | undefined;
  columns?: number | undefined;
  rows?: number | undefined;
}) {
  const letters = ["A", "B", "C", "D", "E", "F"];
  return (
    <div className="mb-map-grid" data-refs={refs ? "true" : "false"}>
      {refs ? (
        <div className="mb-map-refs-x" aria-hidden="true">
          {Array.from({ length: columns }, (_, index) => (
            <span key={index}>W{index - (columns - 1)}</span>
          ))}
        </div>
      ) : null}
      <div className="mb-map-sheet">
        {refs ? (
          <div className="mb-map-refs-y" aria-hidden="true">
            {letters.slice(0, rows).map((letter) => (
              <span key={letter}>{letter}</span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
