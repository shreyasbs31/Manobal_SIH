"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";

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
  copy,
}: {
  values: readonly RibbonPoint[];
  label: string;
  variant?: "hero" | "detail" | "empty" | undefined;
  takeaway?: string | undefined;
  copy?:
    | {
        usualRange: string;
        dataTable: string;
        day: string;
        value: string;
        outsideRange: string;
      }
    | undefined;
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
        aria-label={`${sentence}. ${copy?.usualRange ?? "Personal median with a usual-range band."}`}
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
            {copy?.usualRange ?? "Your usual range"}
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
            <title>{`${copy?.day ?? "Day"} ${point.day} ${copy?.outsideRange ?? "is outside the usual range"}`}</title>
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
        <summary>{copy?.dataTable ?? "Data table"}</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">{copy?.day ?? "Day"}</th>
              <th scope="col">{copy?.value ?? "Value"}</th>
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

function Spark({ values }: { values: readonly number[] }) {
  if (values.length < 2) {
    return null;
  }
  const max = Math.max(...values, 1);
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 36;
      const y = 12 - (value / max) * 10;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg aria-hidden="true" className="mb-spark" height="14" width="40">
      <polyline fill="none" points={points} stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function FormationGrid({
  units,
  weeks,
  cells,
  takeaway = "Charlie Coy's workload has risen for three weeks.",
  sparks,
  onSelect,
  copy,
}: {
  units: readonly string[];
  weeks: number;
  cells: readonly FormationCell[];
  takeaway?: string | undefined;
  sparks?: Record<string, readonly number[]> | undefined;
  onSelect?: ((cell: FormationCell & { weekLabel: string }) => void) | undefined;
  copy?:
    | {
        unit?: string;
        hidden?: string;
        usual?: string;
        watch?: string;
        heavy?: string;
        gridLabel?: string;
      }
    | undefined;
}) {
  const reduced = usePrefersReducedMotion();
  const [selected, setSelected] = useState<string | null>(null);
  const [revealedCount, setRevealedCount] = useState(units.length);
  const lookup = new Map(
    cells.map((cell) => [`${cell.unit}-${cell.week}`, cell]),
  );
  const weekLabels = Array.from({ length: weeks }, (_, index) => {
    const offset = weeks - 1 - index;
    return offset === 0 ? "W0" : `W-${offset}`;
  });
  const letters = ["A", "B", "C", "D", "E", "F"];
  const unitLabel = copy?.unit ?? "Unit";
  const hiddenReason =
    copy?.hidden ?? "Hidden to protect individuals. Fewer than 10 people or a recent large change.";
  const gridLabel = copy?.gridLabel ?? "Unit posture by week";

  useEffect(() => {
    if (reduced || revealedCount >= units.length) {
      return;
    }
    let row = 0;
    const timer = window.setInterval(() => {
      row += 1;
      setRevealedCount(row);
      if (row >= units.length) {
        window.clearInterval(timer);
      }
    }, 80);
    return () => window.clearInterval(timer);
  }, [reduced, units.length]);

  return (
    <div
      className="mb-formation-wrap"
      style={
        {
          "--mb-units": units.length,
          "--mb-weeks": weeks,
        } as CSSProperties
      }
    >
      <p className="mb-lay-takeaway">{takeaway}</p>
      <div className="mb-formation" role="grid" aria-label={gridLabel}>
        <span className="mb-formation-head" role="columnheader">
          {unitLabel}
        </span>
        {weekLabels.map((label) => (
          <span className="mb-formation-head" key={label} role="columnheader">
            {label}
          </span>
        ))}
        {units.flatMap((unit, unitIndex) => {
          const shown = unitIndex < revealedCount;
          const letter = letters[unitIndex] ?? unit[0] ?? "A";
          const cells = Array.from({ length: weeks }, (_, index) => {
            const week = index + 1;
            const cell = lookup.get(`${unit}-${week}`);
            const key = `${unit}-${week}`;
            const weekLabel = weekLabels[index] ?? `W${week}`;
            if (!cell || cell.band === "hidden") {
              return (
                <button
                  aria-pressed={selected === key}
                  className="mb-hidden-select"
                  data-revealed={shown ? "true" : "false"}
                  key={key}
                  onClick={() => {
                    setSelected(key);
                    onSelect?.({
                      unit,
                      week,
                      band: "hidden",
                      weekLabel,
                    });
                  }}
                  title={hiddenReason}
                  type="button"
                >
                  <HiddenTile compact reason={hiddenReason} />
                </button>
              );
            }
            return (
              <button
                aria-pressed={selected === key}
                className="mb-tile"
                data-band={cell.band}
                data-revealed={shown ? "true" : "false"}
                data-step={bandStep(cell.band)}
                key={key}
                onClick={() => {
                  setSelected(key);
                  onSelect?.({ ...cell, weekLabel });
                }}
                title={cell.shareLabel ?? `${unit} ${weekLabel}`}
                type="button"
              >
                <span className="mb-sr">{cell.shareLabel ?? cell.band}</span>
              </button>
            );
          });
          return [
            <div
              className="mb-formation-unit"
              data-revealed={shown ? "true" : "false"}
              key={`${unit}-label`}
              role="rowheader"
            >
              <span className="mb-formation-ref">{letter}</span>
              {unit}
              {sparks?.[unit] ? <Spark values={sparks[unit] ?? []} /> : null}
            </div>,
            ...cells,
          ];
        })}
      </div>
      <p className="mb-formation-legend">
        <span>
          <i className="mb-formation-swatch" data-tone="usual" />
          {copy?.usual ?? "Usual"}
        </span>
        <span>
          <i className="mb-formation-swatch" data-tone="watch" />
          {copy?.watch ?? "Watch"}
        </span>
        <span>
          <i className="mb-formation-swatch" data-tone="heavy" />
          {copy?.heavy ?? "Heavy"}
        </span>
        <span>
          <i className="mb-formation-swatch" data-tone="hidden" />
          {copy?.hidden ?? "Hidden to protect individuals"}
        </span>
      </p>
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
  predictedLabel = "Predicted",
  observedLabel = "Observed",
}: {
  points: readonly { predicted: number; observed: number }[];
  predictedLabel?: string | undefined;
  observedLabel?: string | undefined;
}) {
  const width = 360;
  const height = 240;
  const pad = { l: 48, r: 16, t: 16, b: 40 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const x = (value: number) => pad.l + Math.min(1, Math.max(0, value)) * innerW;
  const y = (value: number) => pad.t + (1 - Math.min(1, Math.max(0, value))) * innerH;
  const ticks = [0, 0.5, 1];
  const path = useMemo(
    () =>
      points
        .map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.predicted).toFixed(1)} ${y(point.observed).toFixed(1)}`)
        .join(" "),
    [points],
  );
  return (
    <svg
      className="mb-reliability"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${observedLabel} versus ${predictedLabel}. The diagonal is perfect calibration.`}
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line
            x1={pad.l}
            x2={width - pad.r}
            y1={y(tick)}
            y2={y(tick)}
            stroke="currentColor"
            strokeOpacity="0.12"
          />
          <line
            y1={pad.t}
            y2={height - pad.b}
            x1={x(tick)}
            x2={x(tick)}
            stroke="currentColor"
            strokeOpacity="0.12"
          />
          <text className="mb-chart-tick" x={pad.l - 8} y={y(tick) + 4} textAnchor="end">
            {tick.toFixed(1)}
          </text>
          <text className="mb-chart-tick" x={x(tick)} y={height - 18} textAnchor="middle">
            {tick.toFixed(1)}
          </text>
        </g>
      ))}
      <line
        x1={x(0)}
        y1={y(0)}
        x2={x(1)}
        y2={y(1)}
        stroke="currentColor"
        strokeDasharray="5 5"
        strokeOpacity="0.45"
      />
      {path ? <path d={path} fill="none" stroke="currentColor" strokeWidth="2" /> : null}
      {points.map((point) => (
        <circle
          key={`${point.predicted}-${point.observed}`}
          cx={x(point.predicted)}
          cy={y(point.observed)}
          r="5"
          fill="currentColor"
        >
          <title>
            {predictedLabel} {point.predicted.toFixed(2)}, {observedLabel} {point.observed.toFixed(2)}
          </title>
        </circle>
      ))}
      <text className="mb-chart-axis" x={width / 2} y={height - 4} textAnchor="middle">
        {predictedLabel}
      </text>
      <text
        className="mb-chart-axis"
        x={14}
        y={height / 2}
        textAnchor="middle"
        transform={`rotate(-90 14 ${height / 2})`}
      >
        {observedLabel}
      </text>
    </svg>
  );
}

export function LeadTimeChart({
  values,
  medianLabel = "Median",
  daysLabel = "Days",
  countLabel = "Cases",
}: {
  values: readonly number[];
  medianLabel?: string | undefined;
  daysLabel?: string | undefined;
  countLabel?: string | undefined;
}) {
  const width = 360;
  const height = 240;
  const pad = { l: 48, r: 20, t: 20, b: 40 };
  const edges = [0, 1, 2, 4, 7, 14, 30];
  const labels = ["0-1", "1-2", "2-4", "4-7", "7-14", "14+"];
  const counts = labels.map((_, index) => {
    const lo = edges[index] ?? 0;
    const hi = edges[index + 1];
    return values.filter((value) => (hi === undefined ? value >= lo : value >= lo && value < hi)).length;
  });
  const max = Math.max(...counts, 1);
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const barW = innerW / counts.length;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median =
    sorted.length === 0
      ? null
      : sorted.length % 2
        ? (sorted[mid] ?? 0)
        : ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2;
  const medianX =
    median === null
      ? null
      : pad.l +
        (median <= 0
          ? 0
          : median >= 14
            ? innerW * 0.92
            : (labels.findIndex((_, index) => {
                const lo = edges[index] ?? 0;
                const hi = edges[index + 1] ?? 30;
                return median >= lo && median < hi;
              }) +
                0.5) *
              barW);
  return (
    <svg
      className="mb-lead-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${countLabel} by ${daysLabel.toLowerCase()} to first action. ${medianLabel}${median === null ? "" : ` ${median.toFixed(1)}`}.`}
    >
      {counts.map((count, index) => {
        const barH = (count / max) * innerH;
        const x = pad.l + index * barW + 6;
        const y = pad.t + innerH - barH;
        return (
          <g key={labels[index]}>
            <rect
              x={x}
              y={y}
              width={barW - 12}
              height={Math.max(barH, count ? 2 : 0)}
              fill="currentColor"
              opacity="0.72"
            />
            <text className="mb-chart-tick" x={x + (barW - 12) / 2} y={height - 18} textAnchor="middle">
              {labels[index]}
            </text>
            {count ? (
              <text className="mb-chart-tick" x={x + (barW - 12) / 2} y={y - 6} textAnchor="middle">
                {count}
              </text>
            ) : null}
          </g>
        );
      })}
      {medianX !== null ? (
        <g>
          <line
            x1={medianX}
            x2={medianX}
            y1={pad.t}
            y2={height - pad.b}
            stroke="currentColor"
            strokeDasharray="5 5"
          />
          <text className="mb-chart-axis" x={Math.min(medianX + 8, width - pad.r)} y={pad.t + 12}>
            {medianLabel} {median?.toFixed(1)}
          </text>
        </g>
      ) : null}
      <text className="mb-chart-axis" x={width / 2} y={height - 4} textAnchor="middle">
        {daysLabel}
      </text>
      <text
        className="mb-chart-axis"
        x={14}
        y={height / 2}
        textAnchor="middle"
        transform={`rotate(-90 14 ${height / 2})`}
      >
        {countLabel}
      </text>
    </svg>
  );
}
