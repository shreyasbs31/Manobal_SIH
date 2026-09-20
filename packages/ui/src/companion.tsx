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
      {normalised.map((line, index) => (
        <p className="mb-caption-line" data-speaker={line.speaker} key={`${line.speaker}-${index}`}>
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
  onJoin,
}: {
  peer: string;
  status: string;
  joinLabel?: string | undefined;
  onJoin?: (() => void) | undefined;
}) {
  return (
    <section className="mb-card mb-call">
      <VoiceOrb state="speaking" label={peer} />
      <p>{status}</p>
      <div className="mb-action-row">
        <button className="mb-primary" onClick={onJoin} type="button">
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
      <i className="mb-phone-btn mb-phone-btn-silent" aria-hidden="true" />
      <i className="mb-phone-btn mb-phone-btn-vol-up" aria-hidden="true" />
      <i className="mb-phone-btn mb-phone-btn-vol-down" aria-hidden="true" />
      <i className="mb-phone-btn mb-phone-btn-power" aria-hidden="true" />
      <div className="mb-phone-bezel">
        <div className="mb-phone-island" aria-hidden="true">
          <span className="mb-phone-cam" />
        </div>
        <div className="mb-phone-screen" title={title}>
          {children}
        </div>
        <div className="mb-phone-home" aria-hidden="true" />
      </div>
    </div>
  );
}

export function ZoneDiagram() {
  const zones = [
    { id: "0", title: "Phone", detail: "Stays with you", blocked: false },
    { id: "1", title: "Unit", detail: "Care and alerts", blocked: false },
    { id: "2", title: "Names", detail: "Locked until needed", blocked: false },
    { id: "3", title: "Record", detail: "Who looked, and why", blocked: false },
    { id: "X", title: "Never connected", detail: "Posting and appraisal stay out", blocked: true },
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
