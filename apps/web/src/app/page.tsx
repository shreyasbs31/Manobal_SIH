import { BaselineRibbonChart, PublicHeader } from "@manobal/ui";
import type { Metadata } from "next";
import Link from "next/link";

import { manobalMode } from "@/lib/mode";

export const metadata: Metadata = {
  title: "Support, not surveillance",
};

const stats = [
  {
    figure: "Over 80%",
    claim: "Share of reported incidents among constabulary ranks in public summaries",
    source: "Public reporting on CRPF data",
    date: "2021 to 2025 (verify before citation)",
  },
  {
    figure: "Most on duty",
    claim: "Public summaries of the same years say most incidents occurred while on duty",
    source: "Public reporting on CRPF data",
    date: "2021 to 2025 (verify before citation)",
  },
  {
    figure: "Named stressors",
    claim: "Extended high-risk deployments, service conditions, and family or land disputes",
    source: "Public reporting on the MHA task force draft",
    date: "Date to be verified",
  },
] as const;

const phoneRoles = [
  {
    href: "/login?role=personnel",
    title: "Saathi on a phone",
    detail: "Private check-in, voice companion, toolkit, and rights. This is a PWA at /app, not a native Expo build.",
  },
] as const;

const deskRoles = [
  ["/login?role=uwo", "Welfare officer", "Cases ordered by due time, never by a score"],
  ["/login?role=mo", "Medical officer", "Acute board with a live timer that cannot be switched off"],
  ["/login?role=commander", "Commander", "Unit posture only. No names, no drill-down to a person"],
  ["/login?role=hq", "Force HQ", "Theatre comparison, still grouped"],
  ["/login?role=wdec", "Governance", "Fairness, audit chain, and independent controls"],
] as const;

const mapping = [
  ["Personnel Wellness Monitoring Dashboard", "Welfare Console, Command Console, Force HQ"],
  ["Mobile-based Wellness and Self-Assessment Application", "Saathi PWA"],
  ["Predictive Behavioral Analytics Engine", "Engine baselines, regimes, CUSUM, Validation Lab"],
  ["Stress and Burnout Risk Prediction Models", "14-day forecast with calibration and drivers; CBI burnout domain"],
  ["Welfare Intervention Recommendation System", "Lever library, ranking, closed loop, JITAI"],
  ["Role-based Access Control and Privacy Management Framework", "Roles, grants, vault, Rights Centre, DPO Centre, Trust Centre"],
  ["Automated Alerts for authorized welfare personnel", "Tiered alerts, escalation ladder, acute path"],
  ["Data anonymization and secure storage mechanisms", "Tokenisation, envelope encryption, k-anonymity, audit chain"],
  ["Secure integration with HRMS", "Integration Console"],
] as const;

const ribbon = [
  { day: 1, value: 3.1 },
  { day: 12, value: 3.0 },
  { day: 24, value: 3.3 },
  { day: 36, value: 3.2 },
  { day: 48, value: 4.1 },
  { day: 60, value: 5.2 },
  { day: 72, value: 5.8 },
  { day: 84, value: 5.4 },
] as const;

export default function LandingPage() {
  return (
    <div className="mb-theme mb-landing" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <section className="mb-landing-hero">
        <p className="mb-landing-kicker">Predictive welfare support for CAPF personnel</p>
        <p className="mb-promise">Support, not surveillance</p>
        <h1>A private companion on the phone. Protected group insight on the desk.</h1>
        <p>
          MANOBAL helps a person check in in their own language, helps authorised
          welfare teams act early, and shows commanders only what a small group can
          safely show.
        </p>
        <BaselineRibbonChart label="The ribbon is a person versus their own usual range" values={ribbon} />
        <div className="mb-stats">
          {stats.map((stat) => (
            <article className="mb-stat" key={stat.figure}>
              <strong>{stat.figure}</strong>
              <p>{stat.claim}</p>
              <small>
                Source: {stat.source}. Date: {stat.date}.
              </small>
            </article>
          ))}
        </div>
        <div className="mb-action-row">
          <Link className="mb-primary" href="/app">
            Open Saathi
          </Link>
          <Link className="mb-secondary" href="/stage?phone=/app&console=/command">
            View phone and console together
          </Link>
        </div>
        <div className="mb-roles">
          {phoneRoles.map((role) => (
            <Link className="mb-role" href={role.href} key={role.href}>
              <strong>{role.title}</strong>
              <span>{role.detail}</span>
            </Link>
          ))}
          {deskRoles.map(([href, title, detail]) => (
            <Link className="mb-role" href={href} key={href}>
              <strong>{title}</strong>
              <span>{detail}</span>
            </Link>
          ))}
        </div>
      </section>
      <section className="mb-mapping">
        <h2>How the problem statement maps to screens</h2>
        {mapping.map(([component, where]) => (
          <div className="mb-map-row" key={component}>
            <strong>{component}</strong>
            <span>{where}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
