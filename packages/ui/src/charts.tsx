import { Lock } from "lucide-react";

export interface RibbonPoint {
  day: number;
  value: number;
}

function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const left = sorted[mid - 1];
  const right = sorted[mid];
  if (sorted.length === 0 || right === undefined) {
    return 0;
  }
  if (sorted.length % 2 === 0 && left !== undefined) {
    return (left + right) / 2;
  }
  return right;
}

function mad(values: readonly number[], centre: number): number {
  const deviations = values.map((value) => Math.abs(value - centre));
  return Math.max(median(deviations), 0.35);
}

export function BaselineRibbonChart({
  values,
  label,
}: {
  values: readonly RibbonPoint[];
  label: string;
}) {
  const width = 320;
  const height = 140;
  const pad = 16;
  const series = values.map((point) => point.value);
  const centre = median(series);
  const spread = mad(series, centre);
  const minValue = Math.min(...series, centre - spread) - 0.4;
  const maxValue = Math.max(...series, centre + spread) + 0.4;
  const x = (day: number) => {
    const first = values[0]?.day ?? 0;
    const last = values[values.length - 1]?.day ?? 1;
    const span = Math.max(last - first, 1);
    return pad + ((day - first) / span) * (width - pad * 2);
  };
  const y = (value: number) => {
    const span = Math.max(maxValue - minValue, 0.1);
    return height - pad - ((value - minValue) / span) * (height - pad * 2);
  };
  const line = values
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${x(point.day).toFixed(1)} ${y(point.value).toFixed(1)}`;
    })
    .join(" ");
  const bandTop = y(centre + spread);
  const bandBottom = y(centre - spread);
  const outOfBand = values.filter(
    (point) => Math.abs(point.value - centre) > spread,
  );

  return (
    <figure className="mb-card" style={{ margin: 0 }}>
      <figcaption style={{ marginBottom: 8 }}>{label}</figcaption>
      <svg
        className="mb-ribbon-chart"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${label}: personal median with spread band. Markers show days outside the usual range.`}
      >
        <rect
          className="mb-ribbon-band"
          x={pad}
          y={bandTop}
          width={width - pad * 2}
          height={Math.max(bandBottom - bandTop, 8)}
        />
        <line
          className="mb-ribbon-median"
          x1={pad}
          x2={width - pad}
          y1={y(centre)}
          y2={y(centre)}
        />
        <path className="mb-ribbon-line" d={line} />
        {outOfBand.map((point) => (
          <circle
            className="mb-ribbon-marker"
            key={point.day}
            cx={x(point.day)}
            cy={y(point.value)}
            r={4}
          >
            <title>{`Day ${point.day} is outside the usual range`}</title>
          </circle>
        ))}
      </svg>
    </figure>
  );
}

export interface FormationCell {
  unit: string;
  week: number;
  band: "T0" | "T1" | "T2" | "T3" | "T4" | "hidden";
  shareLabel?: string | undefined;
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
      <Lock size={12} aria-hidden="true" />
      <span className={compact ? "mb-sr" : undefined}>{reason}</span>
    </span>
  );
}

export function FormationGrid({
  units,
  weeks,
  cells,
}: {
  units: readonly string[];
  weeks: number;
  cells: readonly FormationCell[];
}) {
  const lookup = new Map(
    cells.map((cell) => [`${cell.unit}-${cell.week}`, cell]),
  );
  return (
    <table className="mb-formation" aria-label="Unit posture by week">
      <thead>
        <tr>
          <th scope="col">Unit</th>
          {Array.from({ length: weeks }, (_, index) => (
            <th key={index} scope="col">
              W{index + 1}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {units.map((unit) => (
          <tr key={unit}>
            <th scope="row">{unit}</th>
            {Array.from({ length: weeks }, (_, index) => {
              const cell = lookup.get(`${unit}-${index + 1}`);
              if (!cell || cell.band === "hidden") {
                return (
                  <td key={`${unit}-${index}`}>
                    <HiddenTile
                      compact
                      reason="Hidden: group too small to show"
                    />
                  </td>
                );
              }
              return (
                <td key={`${unit}-${index}`}>
                  <span
                    className="mb-tile"
                    data-band={cell.band}
                    title={cell.shareLabel ?? `${unit} week ${index + 1} ${cell.band}`}
                  >
                    <span className="mb-sr">
                      {cell.shareLabel ?? cell.band}
                    </span>
                  </span>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
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
  const path = points
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${point.predicted * 180 + 10} ${180 - point.observed * 160}`;
    })
    .join(" ");
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
