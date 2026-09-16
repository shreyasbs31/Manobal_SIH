"use client";

import type { ReactNode } from "react";

export function VoiceOrb({
  state = "idle",
  label = "Saathi",
}: {
  state?: "idle" | "listening" | "speaking" | undefined;
  label?: string | undefined;
}) {
  return (
    <div
      aria-label={`${label}, ${state}`}
      className="mb-orb"
      data-state={state}
      role="img"
    >
      <span className="mb-orb-ring" aria-hidden="true" />
      <span className="mb-orb-core" aria-hidden="true" />
      <span className="mb-sr">{label}, {state}</span>
    </div>
  );
}

export function CaptionStream({
  language,
  lines,
}: {
  language: string;
  lines: readonly string[];
}) {
  return (
    <div className="mb-captions" aria-live="polite">
      <span className="mb-chip">{language}</span>
      {lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
    </div>
  );
}

export function SOSButton({ href = "/app/me" }: { href?: string | undefined }) {
  return (
    <a className="mb-sos-btn" href={href}>
      SOS
    </a>
  );
}

export function CallPanel({
  peer,
  status,
}: {
  peer: string;
  status: string;
}) {
  return (
    <section className="mb-card mb-call">
      <VoiceOrb state="speaking" label={peer} />
      <p>{status}</p>
      <div className="mb-action-row">
        <button className="mb-primary" type="button">
          Join call
        </button>
        <button className="mb-secondary" type="button">
          Leave
        </button>
      </div>
    </section>
  );
}

export function PhoneFrame({
  children,
  title = "Saathi on a phone",
}: {
  children: ReactNode;
  title?: string | undefined;
}) {
  return (
    <div className="mb-phone">
      <div className="mb-phone-ear" aria-hidden="true" />
      <div className="mb-phone-screen" title={title}>
        {children}
      </div>
    </div>
  );
}

export function ZoneDiagram() {
  const zones = [
    { id: "0", title: "Zone 0", detail: "On the phone", blocked: false },
    { id: "1", title: "Zone 1", detail: "Engine", blocked: false },
    { id: "2", title: "Zone 2", detail: "Vault", blocked: false },
    { id: "3", title: "Zone 3", detail: "Audit", blocked: false },
    { id: "X", title: "Zone X", detail: "Blocked path", blocked: true },
  ] as const;
  return (
    <div className="mb-zone">
      {zones.map((zone) => (
        <figure data-blocked={zone.blocked ? "true" : "false"} key={zone.id}>
          <strong>{zone.title}</strong>
          <p>{zone.detail}</p>
        </figure>
      ))}
    </div>
  );
}
