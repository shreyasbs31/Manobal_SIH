"use client";

import type { ReactNode } from "react";

import { VoiceContour, type VoiceState } from "./voice-contour";

export function VoiceOrb({
  state = "idle",
  label = "Saathi",
  amplitude = 0.4,
}: {
  state?: VoiceState | undefined;
  label?: string | undefined;
  amplitude?: number | undefined;
}) {
  return (
    <div className="mb-voice-wrap">
      <VoiceContour amplitude={amplitude} state={state === "idle" ? "listening" : state} />
      <span className="mb-sr">{label}, {state}</span>
    </div>
  );
}

export function CaptionStream({
  language,
  lines,
}: {
  language: string;
  lines: readonly { speaker: "you" | "saathi"; text: string }[] | readonly string[];
}) {
  const normalised = lines.map((line) =>
    typeof line === "string"
      ? { speaker: line.startsWith("You") ? "you" : "saathi", text: line }
      : line,
  );
  return (
    <div className="mb-captions" aria-live="polite">
      {language ? <span className="mb-chip">{language}</span> : null}
      {normalised.map((line) => (
        <p className="mb-caption-line" data-speaker={line.speaker} key={line.text}>
          {line.speaker === "you" ? "You: " : "Saathi: "}
          {line.text}
        </p>
      ))}
    </div>
  );
}

export function SOSButton({ href = "/app/safety" }: { href?: string | undefined }) {
  return (
    <a className="mb-sos-btn" href={href}>
      SOS
    </a>
  );
}

export function CallPanel({
  peer,
  status,
  joinLabel = "Join call",
}: {
  peer: string;
  status: string;
  joinLabel?: string | undefined;
}) {
  return (
    <section className="mb-card mb-call">
      <VoiceOrb state="speaking" label={peer} />
      <p>{status}</p>
      <div className="mb-action-row">
        <button className="mb-primary" type="button">
          {joinLabel}
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
