"use client";

import type { ReactNode } from "react";

import { DomainChip, LimitedDataTag, TierBadge, TrajectoryArrow } from "./badges";
import type { TierId, Trajectory } from "./types";

export function SlaTimer({
  label,
  remainingLabel,
  urgent = false,
}: {
  label: string;
  remainingLabel: string;
  urgent?: boolean | undefined;
}) {
  return (
    <span className="mb-sla" data-urgent={urgent ? "true" : "false"}>
      <span>{label}</span>
      <strong className="mb-num">{remainingLabel}</strong>
    </span>
  );
}

export function EscalationLadder({
  steps,
  current,
}: {
  steps: readonly string[];
  current: string;
}) {
  return (
    <ol className="mb-ladder" aria-label="Escalation ladder">
      {steps.map((step) => (
        <li
          className="mb-ladder-step"
          data-current={step === current ? "true" : "false"}
          key={step}
        >
          {step}
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
  lever,
  sla,
  status,
  source,
}: {
  caseId: string;
  tier: TierId;
  trajectory: Trajectory;
  limited: boolean;
  domains: readonly string[];
  drift: string;
  lever: string;
  sla: string;
  status: string;
  source: string;
}) {
  return (
    <article className="mb-card mb-case">
      <div className="mb-case-head">
        <strong>{caseId}</strong>
        <TierBadge tier={tier} />
        <TrajectoryArrow direction={trajectory} />
        {limited ? <LimitedDataTag /> : null}
      </div>
      <div className="mb-action-row">
        {domains.map((domain) => (
          <DomainChip key={domain} label={domain} />
        ))}
      </div>
      <p>{drift}</p>
      <p>Recommended: {lever}</p>
      <SlaTimer label="Due" remainingLabel={sla} urgent={tier === "T4"} />
      <p>
        {status}. Source: {source}
      </p>
    </article>
  );
}

export function LeverOption({
  title,
  rationale,
  hint,
}: {
  title: string;
  rationale: string;
  hint: string;
}) {
  return (
    <label className="mb-card" style={{ display: "grid", gap: 8 }}>
      <span>
        <input name="lever" type="radio" value={title} /> {title}
      </span>
      <p>{rationale}</p>
      <p>{hint}</p>
    </label>
  );
}

export function BriefPanel({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <aside className="mb-card mb-brief">
      <p className="mb-chip">AI-written, check before use</p>
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
    <article className="mb-card mb-kpi">
      <span>{label}</span>
      <strong className="mb-num">{value}</strong>
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
}: {
  title: string;
  leavesPhone: string;
  whoCanSee: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <article className="mb-card mb-toggle">
      <div className="mb-toggle-row">
        <h3>{title}</h3>
        <button
          aria-pressed={checked}
          className="mb-secondary"
          onClick={() => onChange(!checked)}
          type="button"
        >
          {checked ? "On" : "Off"}
        </button>
      </div>
      <p>What leaves your phone: {leavesPhone}</p>
      <p>Who can ever see this: {whoCanSee}</p>
      <p>Change anytime.</p>
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
  return (
    <article className="mb-card">
      <h3>Consent receipt</h3>
      <p className="mb-num">{hash}</p>
      <p>{time}</p>
      <button className="mb-secondary" type="button">
        Download receipt
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
      <span>{when}</span>
      <span>{actor}</span>
      <span>{purpose}</span>
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

export function ChainStatus({ intact }: { intact: boolean }) {
  return (
    <span className="mb-chain">
      <span className="mb-status-dot" aria-hidden="true" />
      Audit chain {intact ? "intact" : "tampered"}
    </span>
  );
}
