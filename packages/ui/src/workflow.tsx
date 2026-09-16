"use client";

import type { ReactNode } from "react";

import { DomainChip, LimitedDataTag, TierBadge, TrajectoryArrow } from "./badges";
import { IconVaultKey } from "./icons";
import type { TierId, Trajectory } from "./types";

export function slaTone(
  remainingRatio: number,
  tier: TierId,
): "calm" | "brass" | "marigold" | "acute" {
  if (tier === "T4") {
    return "acute";
  }
  if (remainingRatio < 0.2) {
    return "marigold";
  }
  if (remainingRatio < 0.5) {
    return "brass";
  }
  return "calm";
}

export function SlaTimer({
  label,
  remainingLabel,
  remainingRatio = 0.6,
  tier = "T2",
  urgent = false,
}: {
  label: string;
  remainingLabel: string;
  remainingRatio?: number | undefined;
  tier?: TierId | undefined;
  urgent?: boolean | undefined;
}) {
  const tone = slaTone(urgent ? 0.1 : remainingRatio, urgent ? "T4" : tier);
  return (
    <span className="mb-sla mb-type-timer" data-tone={tone}>
      <span>{label}</span>
      <strong className="mb-num">{remainingLabel}</strong>
    </span>
  );
}

export function EscalationLadder({
  steps,
  current,
}: {
  steps: readonly string[] | readonly { role: string; status: string; time: string }[];
  current?: string | undefined;
}) {
  const resolved = steps.map((step) =>
    typeof step === "string"
      ? {
          role: step,
          status: step === current ? "acknowledged" : "waiting",
          time: "",
        }
      : step,
  );
  return (
    <ol className="mb-ladder" aria-label="Escalation ladder">
      {resolved.map((step) => (
        <li className="mb-ladder-step" data-status={step.status} key={step.role}>
          <strong>{step.role}</strong>
          <span>{step.status}</span>
          {step.time ? <time>{step.time}</time> : null}
        </li>
      ))}
    </ol>
  );
}

export function CaseCard({
  caseId,
  tier,
  trajectory,
  limited,
  domains,
  drift,
  sla,
  remainingRatio = 0.4,
  lever,
  status,
  source,
}: {
  caseId: string;
  tier: TierId;
  trajectory: Trajectory;
  limited: boolean;
  domains: readonly string[];
  drift: string;
  sla: string;
  remainingRatio?: number | undefined;
  lever?: string | undefined;
  status?: string | undefined;
  source?: string | undefined;
}) {
  const shown = domains.slice(0, 3);
  const extra = domains.length - shown.length;
  return (
    <article className="mb-case" data-tier={tier}>
      <div className="mb-case-head">
        <TierBadge tier={tier} />
        <strong className="mb-num">{caseId}</strong>
        <TrajectoryArrow direction={trajectory} />
        {limited ? <LimitedDataTag /> : null}
        <SlaTimer
          label="SLA"
          remainingLabel={sla}
          remainingRatio={remainingRatio}
          tier={tier}
        />
      </div>
      <div className="mb-case-chips">
        {shown.map((domain) => (
          <DomainChip key={domain} label={domain} />
        ))}
        {extra > 0 ? <span className="mb-chip">+{extra}</span> : null}
      </div>
      <p>{drift}</p>
      {lever ? <p className="mb-sr">Recommended: {lever}</p> : null}
      {status ? <p className="mb-sr">{status}. {source}</p> : null}
    </article>
  );
}

export function CaseStrip({
  days,
  onsetDay,
  incidents = [],
  actions = [],
}: {
  days: readonly { day: number; tier: TierId }[];
  onsetDay: number;
  incidents?: readonly number[] | undefined;
  actions?: readonly number[] | undefined;
}) {
  return (
    <svg
      className="mb-case-strip"
      viewBox="0 0 240 28"
      role="img"
      aria-label="120-day stepped tier band"
    >
      {days.map((point, index) => (
        <rect
          data-tier={point.tier}
          height="12"
          key={point.day}
          width={240 / Math.max(days.length, 1)}
          x={(index * 240) / Math.max(days.length, 1)}
          y="10"
        />
      ))}
      <line
        className="mb-onset"
        x1={(onsetDay / 120) * 240}
        x2={(onsetDay / 120) * 240}
        y1="4"
        y2="24"
      />
      {incidents.map((day) => (
        <polygon
          key={`i-${day}`}
          points={`${(day / 120) * 240},6 ${(day / 120) * 240 - 3},12 ${(day / 120) * 240 + 3},12`}
        />
      ))}
      {actions.map((day) => (
        <rect
          fill="currentColor"
          height="4"
          key={`a-${day}`}
          width="4"
          x={(day / 120) * 240 - 2}
          y="18"
        />
      ))}
    </svg>
  );
}

export function LeverOption({
  title,
  rationale,
  hint,
  index = 1,
}: {
  title: string;
  rationale: string;
  hint: string;
  index?: number | undefined;
}) {
  return (
    <label className="mb-lever">
      <span>
        <input name="lever" type="radio" value={title} /> {index}. {title}
      </span>
      <p>{rationale}</p>
      <p>{hint}</p>
    </label>
  );
}

export function BriefPanel({ children }: { children: ReactNode }) {
  return (
    <aside className="mb-card mb-brief">
      <p>Written by Saathi AI, check before use</p>
      <div>{children}</div>
    </aside>
  );
}

export function KpiTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <article className="mb-kpi">
      <span className="mb-type-section">{label}</span>
      <strong className="mb-type-numeral">{value}</strong>
      <span>{hint}</span>
    </article>
  );
}

export function ConsentToggleCard({
  title,
  leavesPhone,
  whoCanSee,
  checked,
  onChange,
  illustration,
}: {
  title: string;
  leavesPhone: string;
  whoCanSee: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  illustration?: ReactNode | undefined;
}) {
  return (
    <article className="mb-consent">
      {illustration ? <div className="mb-consent-illust">{illustration}</div> : null}
      <div className="mb-consent-copy">
        <h3>{title}</h3>
        <p>What leaves your phone: {leavesPhone}</p>
        <p>Who can ever see this: {whoCanSee}</p>
      </div>
      <button
        aria-pressed={checked}
        className="mb-toggle"
        onClick={() => onChange(!checked)}
        type="button"
      >
        {checked ? "On" : "Off"}
      </button>
    </article>
  );
}

export function ReceiptCard({
  hash,
  time,
}: {
  hash: string;
  time: string;
}) {
  const first = hash.slice(0, Math.ceil(hash.length / 2));
  const second = hash.slice(Math.ceil(hash.length / 2));
  return (
    <article className="mb-receipt">
      <svg className="mb-receipt-perf" viewBox="0 0 200 8" aria-hidden="true">
        <path d="M0 4 Q 6 0 12 4 T 24 4 T 36 4 T 48 4 T 60 4 T 72 4 T 84 4 T 96 4 T 108 4 T 120 4 T 132 4 T 144 4 T 156 4 T 168 4 T 180 4 T 192 4" />
      </svg>
      <h3>Consent receipt</h3>
      <p className="mb-num">{first}</p>
      <p className="mb-num">{second}</p>
      <p>{time}</p>
      <button className="mb-secondary" type="button">
        Download
      </button>
    </article>
  );
}

export function AccessLedgerItem({
  when,
  actor,
  purpose,
}: {
  when: string;
  actor: string;
  purpose: string;
}) {
  return (
    <div className="mb-ledger">
      <IconVaultKey height={18} width={18} />
      <div>
        <p>{actor}</p>
        <p>{purpose}</p>
      </div>
      <time>{when}</time>
    </div>
  );
}

export function AuditRow({
  when,
  action,
  token,
}: {
  when: string;
  action: string;
  token: string;
}) {
  return (
    <div className="mb-audit">
      <span>{when}</span>
      <span>{action}</span>
      <span className="mb-num">{token}</span>
    </div>
  );
}

export function ChainStatus({
  intact = true,
  mode,
}: {
  intact?: boolean | undefined;
  mode?: "intact" | "verify" | "tamper" | "heal" | undefined;
}) {
  const resolved = mode ?? (intact ? "intact" : "tamper");
  return (
    <div className="mb-chain" data-mode={resolved}>
      {Array.from({ length: 12 }, (_, index) => (
        <span
          className="mb-chain-block"
          data-break={resolved === "tamper" && index === 7 ? "true" : "false"}
          key={index}
        />
      ))}
      <span className="mb-sr">
        Audit chain {resolved === "tamper" ? "tampered" : "intact"}
      </span>
    </div>
  );
}
