import type { ReactElement } from "react";

import type { ManobalMode, TierId, Trajectory } from "./types";
import { TIER_LABELS } from "./types";

function DropIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="M10 2 C10 2 4 10 4 13.2 A6 6 0 0 0 16 13.2 C16 10 10 2 10 2 Z"
        fill="currentColor"
      />
    </svg>
  );
}

function TriangleIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 3 L18 17 H2 Z" fill="currentColor" />
    </svg>
  );
}

function DiamondIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 2 L18 10 L10 18 L2 10 Z" fill="currentColor" />
    </svg>
  );
}

function OctagonIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="M7 2 H13 L18 7 V13 L13 18 H7 L2 13 V7 Z"
        fill="currentColor"
      />
    </svg>
  );
}

const TIER_ICONS: Record<TierId, () => ReactElement> = {
  T0: () => (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="7" fill="currentColor" />
    </svg>
  ),
  T1: DropIcon,
  T2: TriangleIcon,
  T3: DiamondIcon,
  T4: OctagonIcon,
};

export function TierBadge({ tier }: { tier: TierId }) {
  const Icon = TIER_ICONS[tier];
  return (
    <span className="mb-tier" data-tier={tier}>
      <Icon />
      <span>
        {tier} {TIER_LABELS[tier]}
      </span>
    </span>
  );
}

export function TrajectoryArrow({ direction }: { direction: Trajectory }) {
  const label =
    direction === "rising"
      ? "Rising"
      : direction === "easing"
        ? "Easing"
        : "Steady";
  const mark = direction === "rising" ? "↑" : direction === "easing" ? "↓" : "→";
  return (
    <span className="mb-traj" aria-label={`Trajectory ${label}`}>
      <span aria-hidden="true">{mark}</span>
      {label}
    </span>
  );
}

export function LimitedDataTag() {
  return <span className="mb-limited">Limited data</span>;
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
    <span className="mb-mode">{mode === "demo" ? "Demo mode" : "Sovereign mode"}</span>
  );
}

export function SimClock({
  value,
  playing = false,
}: {
  value: string;
  playing?: boolean | undefined;
}) {
  return (
    <time className="mb-sim" dateTime={value}>
              Simulated {value}
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

export function AudioClearedChip() {
  return <span className="mb-audio">Audio cleared</span>;
}

export function ValidatedBadge() {
  return <span className="mb-validated">Validated translation</span>;
}

export function MachineTranslatedBadge() {
  return <span className="mb-translated">Machine translated</span>;
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
