import type { ManobalMode, TierId, Trajectory } from "./types";
import { TIER_LABELS } from "./types";
import { TierGlyph } from "./icons";

function DiamondIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 2 L18 10 L10 18 L2 10 Z" fill="currentColor" />
    </svg>
  );
}

export function TierBadge({
  tier,
  caption,
}: {
  tier: TierId;
  caption?: string | undefined;
}) {
  return (
    <span className="mb-tier" data-tier={tier}>
      <TierGlyph tier={tier} />
      <span>
        {tier} {caption ?? TIER_LABELS[tier]}
      </span>
    </span>
  );
}

export function TrajectoryArrow({
  direction,
  labels,
}: {
  direction: Trajectory;
  labels?: { rising: string; easing: string; steady: string } | undefined;
}) {
  const label =
    direction === "rising"
      ? (labels?.rising ?? "Rising")
      : direction === "easing"
        ? (labels?.easing ?? "Easing")
        : (labels?.steady ?? "Steady");
  const mark = direction === "rising" ? "↑" : direction === "easing" ? "↓" : "→";
  return (
    <span className="mb-traj" aria-label={`Trajectory ${label}`}>
      <span aria-hidden="true">{mark}</span>
      {label}
    </span>
  );
}

export function LimitedDataTag({ label = "Limited data" }: { label?: string | undefined }) {
  return <span className="mb-limited">{label}</span>;
}

export function DomainChip({ label }: { label: string }) {
  return <span className="mb-domain">{label}</span>;
}

export function DriverList({ items }: { items: readonly string[] }) {
  return (
    <ul className="mb-drivers">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function ModeChip({ mode }: { mode: ManobalMode }) {
  return (
    <span className="mb-status-chip" data-kind="demo">
      {mode === "demo" ? "Demo" : "Sovereign"}
    </span>
  );
}

export function StatusChip({
  kind,
  queued = 0,
  label: customLabel,
}: {
  kind: "offline" | "syncing" | "demo";
  queued?: number | undefined;
  label?: string | undefined;
}) {
  const label =
    customLabel ??
    (kind === "offline"
      ? queued > 0
        ? `Offline. ${queued} check-ins saved on this phone.`
        : "Offline"
      : kind === "syncing"
        ? "Syncing"
        : "Demo");
  return (
    <span className="mb-status-chip" data-kind={kind}>
      {kind === "offline" ? <span className="mb-status-dot" aria-hidden="true" /> : null}
      {label}
    </span>
  );
}

export function SimClock({
  value,
  playing = false,
  prefix = "",
}: {
  value: string;
  playing?: boolean | undefined;
  prefix?: string | undefined;
}) {
  return (
    <time className="mb-sim mb-type-timer" dateTime={value}>
      {prefix ? `${prefix} ` : ""}{value}
    </time>
  );
}

export function OfflineChip({ offline }: { offline: boolean }) {
  return (
    <span
      className="mb-offline"
      data-state={offline ? "offline" : "online"}
    >
      <span className="mb-status-dot" aria-hidden="true" />
      {offline ? "Offline" : "Online"}
    </span>
  );
}

export function SyncQueueIndicator({ count }: { count: number }) {
  return (
    <span className="mb-sync">
      Queued {count} {count === 1 ? "item" : "items"}
    </span>
  );
}

export function AudioClearedChip({
  ms,
  label,
}: {
  ms?: number | undefined;
  label?: string | undefined;
} = {}) {
  const resolved = label ?? (ms === undefined ? "Audio cleared" : `Audio cleared in ${ms} ms`);
  return <span className="mb-audio">{resolved}</span>;
}

export function ValidatedBadge({ label = "Validated translation" }: { label?: string | undefined } = {}) {
  return <span className="mb-validated">{label}</span>;
}

export function MachineTranslatedBadge({ label = "Machine translated" }: { label?: string | undefined } = {}) {
  return <span className="mb-translated">{label}</span>;
}

export function ProviderBadge({ name }: { name: string }) {
  return <span className="mb-provider">Provider: {name}</span>;
}

export function EmptyState({
  title = "Nothing here yet",
  message = "New items will appear here when they are available.",
}: {
  title?: string | undefined;
  message?: string | undefined;
}) {
  return (
    <section className="mb-card mb-state" aria-live="polite">
      <RibbonGlyph />
      <div>
        <h2>{title}</h2>
        <p>{message}</p>
      </div>
    </section>
  );
}

export function ErrorState({
  retry,
}: {
  retry?: (() => void) | undefined;
}) {
  return (
    <section className="mb-card mb-state" role="alert">
      <DiamondIcon />
      <div>
        <h2>We could not load this view</h2>
        <p>Check the connection and try again.</p>
        {retry ? (
          <button className="mb-primary" type="button" onClick={retry}>
            Try again
          </button>
        ) : null}
      </div>
    </section>
  );
}

export function LoadingState() {
  return (
    <section className="mb-card mb-state" aria-live="polite" aria-busy="true">
      <RibbonGlyph />
      <div>
        <h2>Loading</h2>
        <p>Preparing this view.</p>
      </div>
    </section>
  );
}

function RibbonGlyph() {
  return (
    <svg
      width="36"
      height="18"
      viewBox="0 0 36 18"
      aria-hidden="true"
      className="mb-ribbon-mark"
    >
      <path d="M1 11 C8 3 14 4 20 9 S30 16 35 7" />
    </svg>
  );
}
