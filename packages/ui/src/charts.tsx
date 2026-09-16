"use client";

import { useEffect, useMemo, useState } from "react";

import { IconHiddenLock } from "./icons";
import { usePrefersReducedMotion } from "./motion";

export interface RibbonPoint {
  day: number;
  value: number;
}

function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 0) {
    return 0;
  }
  const mid = Math.floor(sorted.length / 2);
  const right = sorted[mid];
  if (right === undefined) {
    return 0;
  }
  if (sorted.length % 2 === 0) {
    const left = sorted[mid - 1];
    return left === undefined ? right : (left + right) / 2;
  }
  return right;
}

function mad(values: readonly number[], centre: number): number {
  return Math.max(
    median(values.map((value) => Math.abs(value - centre))),
    0.2,
  );
}

function monotonePath(
  points: readonly { x: number; y: number }[],
): string {
  if (points.length === 0) {
    return "";
  }
  const first = points[0];
  if (!first) {
    return "";
  }
  if (points.length === 1) {
    return `M ${first.x.toFixed(1)} ${first.y.toFixed(1)}`;
  }
  const dx: number[] = [];
  const dy: number[] = [];
  const m: number[] = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    if (!a || !b) {
      continue;
    }
    const span = b.x - a.x || 1;
    dx.push(span);
    dy.push((b.y - a.y) / span);
  }
  m.push(dy[0] ?? 0);
  for (let i = 1; i < dy.length; i += 1) {
    const prev = dy[i - 1] ?? 0;
    const curr = dy[i] ?? 0;
    if (prev * curr <= 0) {
      m.push(0);
    } else {
      m.push((prev + curr) / 2);
    }
  }
  m.push(dy[dy.length - 1] ?? 0);
  let d = `M ${first.x.toFixed(1)} ${first.y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const span = dx[i] ?? 1;
    const m1 = m[i] ?? 0;
    const m2 = m[i + 1] ?? 0;
    if (!a || !b) {
      continue;
    }
    const c1x = a.x + span / 3;
    const c1y = a.y + (m1 * span) / 3;
    const c2x = b.x - span / 3;
    const c2y = b.y - (m2 * span) / 3;
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
  }
  return d;
}

export function ribbonStats(values: readonly RibbonPoint[]): {
  centre: number;
  spread: number;
} {
  const series = values.map((point) => point.value);
  const centre = median(series);
  const spread = 1.4826 * mad(series, centre);
  return { centre, spread };
}

export function BaselineRibbonChart({
  values,
  label,
  variant = "hero",
  takeaway,
}: {
  values: readonly RibbonPoint[];
  label: string;
  variant?: "hero" | "detail" | "empty" | undefined;
  takeaway?: string | undefined;
}) {
  const reduced = usePrefersReducedMotion();
  const width = variant === "hero" ? 360 : 640;
  const height = variant === "hero" ? 180 : 160;
  const pad = variant === "hero" ? 12 : 28;
  const stats = ribbonStats(values);
  const { centre, spread } = stats;
  const series = values.map((point) => point.value);
  const minValue =
    series.length === 0
      ? 0
      : Math.min(...series, centre - spread) - 0.35;
  const maxValue =
    series.length === 0
      ? 1
      : Math.max(...series, centre + spread) + 0.35;
  const firstDay = values[0]?.day ?? 0;
  const lastDay = values[values.length - 1]?.day ?? 1;
  const spanX = Math.max(lastDay - firstDay, 1);
  const x = (day: number) => pad + ((day - firstDay) / spanX) * (width - pad * 2);
  const y = (value: number) => {
    const span = Math.max(maxValue - minValue, 0.1);
    return height - pad - ((value - minValue) / span) * (height - pad * 2);
  };
  const plotted = values.map((point) => ({
    x: x(point.day),
    y: y(point.value),
  }));
  const line = monotonePath(plotted);
  const bandTop = y(centre + spread);
  const bandBottom = y(centre - spread);
  const outOfBand = values.filter(
    (point) => Math.abs(point.value - centre) > spread,
  );
  const today = values[values.length - 1];
  const sentence =
    takeaway ??
    (variant === "empty"
      ? "Your rhythm appears after a week of check-ins"
      : label);

  if (variant === "empty" || values.length < 2) {
    return (
      <figure className="mb-lay" data-variant="empty">
        <p className="mb-lay-takeaway">{sentence}</p>
        <svg
          className="mb-ribbon-chart"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={sentence}
        >
          <path
            className="mb-ribbon-empty"
            d="M 24 96 C 80 40 140 150 200 90 S 300 40 336 110"
          />
        </svg>
      </figure>
    );
  }

  return (
    <figure className="mb-lay" data-variant={variant}>
      <p className="mb-lay-takeaway">{sentence}</p>
      <svg
        className="mb-ribbon-chart"
        data-reduced={reduced ? "true" : "false"}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${sentence}. Personal median with a usual-range band.`}
      >
        <path
          className="mb-ribbon-band-edge"
          d={`M ${pad} ${bandTop.toFixed(1)} H ${width - pad}`}
        />
        <path
          className="mb-ribbon-band-edge"
          d={`M ${pad} ${bandBottom.toFixed(1)} H ${width - pad}`}
        />
        <rect
          className="mb-ribbon-band"
          x={pad}
          y={bandTop}
          width={width - pad * 2}
          height={Math.max(bandBottom - bandTop, 8)}
        />
        {variant === "detail" ? (
          <text className="mb-ribbon-direct" x={pad} y={Math.max(bandTop - 6, 14)}>
            Your usual range
          </text>
        ) : null}
        <path className="mb-ribbon-line" d={line} />
        {outOfBand.map((point) => (
          <circle
            className="mb-ribbon-marker"
            key={point.day}
            cx={x(point.day)}
            cy={y(point.value)}
            r={4.5}
          >
            <title>{`Day ${point.day} is outside the usual range`}</title>
          </circle>
        ))}
        {today ? (
          <g className="mb-ribbon-today">
            <circle className="mb-ribbon-glow" cx={x(today.day)} cy={y(today.value)} r={12} />
            <circle cx={x(today.day)} cy={y(today.value)} r={5} />
          </g>
        ) : null}
      </svg>
      <details className="mb-chart-table">
        <summary>Data table</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">Day</th>
              <th scope="col">Value</th>
            </tr>
          </thead>
          <tbody>
            {values.map((point) => (
              <tr key={point.day}>
                <td>{point.day}</td>
                <td>{point.value.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

export interface FormationCell {
  unit: string;
  week: number;
  band: "T0" | "T1" | "T2" | "T3" | "T4" | "hidden";
  shareLabel?: string | undefined;
  spark?: readonly number[] | undefined;
}

export function HiddenTile({
  reason,
  compact = false,
}: {
  reason: string;
  compact?: boolean | undefined;
}) {
  return (
    <span className="mb-hidden-tile" title={reason}>
      <IconHiddenLock width={12} height={12} />
      <span className={compact ? "mb-sr" : undefined}>{reason}</span>
    </span>
  );
}

const BAND_STEPS = ["step-1", "step-2", "step-3", "step-4", "step-5"] as const;

function bandStep(band: FormationCell["band"]): (typeof BAND_STEPS)[number] {
  if (band === "T3" || band === "T4") {
    return "step-5";
  }
  if (band === "T2") {
    return "step-3";
  }
  if (band === "T1") {
    return "step-2";
  }
  return "step-1";
}

export function FormationGrid({
  units,
  weeks,
  cells,
  takeaway = "Charlie Coy's workload has risen for three weeks.",
}: {
  units: readonly string[];
  weeks: number;
  cells: readonly FormationCell[];
  takeaway?: string | undefined;
}) {
  const reduced = usePrefersReducedMotion();
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(reduced ? units.length : 0);
  const lookup = new Map(
    cells.map((cell) => [`${cell.unit}-${cell.week}`, cell]),
  );
  const weekLabels = Array.from({ length: weeks }, (_, index) => {
    const offset = weeks - 1 - index;
    return offset === 0 ? "W0" : `W-${offset}`;
  });
  const letters = ["A", "B", "C", "D", "E", "F"];

  useEffect(() => {
    if (reduced) {
      return;
    }
    let row = 0;
    const timer = window.setInterval(() => {
      row += 1;
      setRevealed(row);
      if (row >= units.length) {
        window.clearInterval(timer);
      }
    }, 80);
    return () => window.clearInterval(timer);
  }, [reduced, units.length]);

  return (
    <div className="mb-formation-wrap">
      <p className="mb-lay-takeaway">{takeaway}</p>
      <table className="mb-formation" aria-label="Unit posture by week">
        <thead>
          <tr>
            <th scope="col">Unit</th>
            {weekLabels.map((label) => (
              <th key={label} scope="col">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {units.map((unit, unitIndex) => (
            <tr
              data-revealed={unitIndex < revealed ? "true" : "false"}
              key={unit}
            >
              <th scope="row">
                <span className="mb-formation-ref">{letters[unitIndex] ?? unit[0]}</span>
                {unit}
              </th>
              {Array.from({ length: weeks }, (_, index) => {
                const week = index + 1;
                const cell = lookup.get(`${unit}-${week}`);
                const key = `${unit}-${week}`;
                if (!cell || cell.band === "hidden") {
                  return (
                    <td key={key}>
                      <HiddenTile
                        compact
                        reason="Hidden to protect individuals. Fewer than 10 people or recent large changes."
                      />
                    </td>
                  );
                }
                return (
                  <td key={key}>
                    <button
                      aria-pressed={selected === key}
                      className="mb-tile"
                      data-band={cell.band}
                      data-step={bandStep(cell.band)}
                      onClick={() => setSelected(key)}
                      title={cell.shareLabel ?? `${unit} ${weekLabels[index]}`}
                      type="button"
                    >
                      <span className="mb-sr">
                        {cell.shareLabel ?? cell.band}
                      </span>
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FairnessBar({
  ratio,
  label,
}: {
  ratio: number;
  label: string;
}) {
  const clamped = Math.min(1.6, Math.max(0.4, ratio));
  const left = ((clamped - 0.4) / 1.2) * 100;
  return (
    <figure className="mb-card" style={{ margin: 0 }}>
      <figcaption>{label}</figcaption>
      <svg
        className="mb-fairness"
        viewBox="0 0 200 40"
        role="img"
        aria-label={`${label}: ratio ${ratio.toFixed(2)}, parity band 0.8 to 1.25`}
      >
        <rect x="0" y="16" width="200" height="8" fill="currentColor" opacity="0.12" />
        <rect
          x={((0.8 - 0.4) / 1.2) * 200}
          y="12"
          width={((1.25 - 0.8) / 1.2) * 200}
          height="16"
          fill="currentColor"
          opacity="0.2"
        />
        <circle cx={left * 2} cy="20" r="6" fill="currentColor" />
      </svg>
    </figure>
  );
}

export function ReliabilityChart({
  points,
}: {
  points: readonly { predicted: number; observed: number }[];
}) {
  const path = useMemo(
    () =>
      points
        .map((point, index) => {
          const command = index === 0 ? "M" : "L";
          return `${command} ${point.predicted * 180 + 10} ${180 - point.observed * 160}`;
        })
        .join(" "),
    [points],
  );
  return (
    <svg
      className="mb-reliability"
      viewBox="0 0 200 180"
      role="img"
      aria-label="Reliability diagram of predicted band versus observed share"
    >
      <line x1="10" y1="170" x2="190" y2="10" stroke="currentColor" opacity="0.3" />
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}
