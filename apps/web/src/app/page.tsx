import { landingRibbon } from "@manobal/contracts";
import {
  SceneBunkDawn,
  SceneCircleSupport,
  SceneEmptyPath,
  SceneHighPost,
  SceneInformalWalk,
} from "@manobal/illustrations";
import { BaselineRibbonChart, ContourTexture, PublicHeader } from "@manobal/ui";
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
    date: "2021 to 2025",
  },
  {
    figure: "Most on duty",
    claim: "Public summaries of the same years say most incidents occurred while on duty",
    source: "Public reporting on CRPF data",
    date: "2021 to 2025",
  },
  {
    figure: "Named stressors",
    claim: "Extended high-risk deployments, service conditions, and family or land disputes",
    source: "Public reporting on the MHA task force draft",
    date: "2021 to 2025",
  },
] as const;

const doors = [
  {
    href: "/login?role=personnel",
    title: "Personnel",
    detail: "Private check-in and a companion on the phone",
    Scene: SceneBunkDawn,
  },
  {
    href: "/login?role=uwo",
    title: "Welfare officer",
    detail: "Cases ordered by due time, never by a score",
    Scene: SceneInformalWalk,
  },
  {
    href: "/login?role=commander",
    title: "Commander",
    detail: "Unit posture only. No names.",
    Scene: SceneHighPost,
  },
  {
    href: "/login?role=wdec",
    title: "Ethics cell",
    detail: "Fairness, audit chain, independent controls",
    Scene: SceneCircleSupport,
  },
  {
    href: "/architecture",
    title: "More",
    detail: "How names stay separate",
    Scene: SceneEmptyPath,
  },
] as const;

export default function LandingPage() {
  return (
    <div className="mb-theme mb-landing" data-skin="saathi" data-theme="light">
      <PublicHeader home mode={manobalMode()} />
      <main>
      <section className="mb-landing-hero">
        <h1>
          Every jawan has a usual rhythm. MANOBAL notices when it changes, and makes sure
          the right person helps.
        </h1>
        <div className="mb-landing-hero-ribbon">
          <ContourTexture height={200} seed="landing" width={1200} />
          <BaselineRibbonChart
            label="A person versus their own usual range"
            takeaway="The line can leave the band. A quiet marker appears. Then it can return."
            values={landingRibbon}
            variant="hero"
          />
        </div>
        <p className="mb-landing-promise">Support, not surveillance.</p>
        <nav aria-label="Role doors" className="mb-roles">
          {doors.map((door) => (
            <Link className="mb-role" href={door.href} key={door.href}>
              <door.Scene />
              <strong>{door.title}</strong>
              <span>{door.detail}</span>
            </Link>
          ))}
        </nav>
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
      </section>
      <section className="mb-mapping" id="ps-map">
        <h2>What each person uses</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Who</th>
              <th scope="col">What they do</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Personnel</th>
              <td>Check in, talk with Saathi, rest, and reach a person when they want one</td>
            </tr>
            <tr>
              <th scope="row">Welfare officer</th>
              <td>Open cases by urgency and due time, never by a score</td>
            </tr>
            <tr>
              <th scope="row">Counsellor</th>
              <td>Take requests, join a call, and keep notes private</td>
            </tr>
            <tr>
              <th scope="row">Medical officer</th>
              <td>Acknowledge urgent cases and stay with the person until someone reaches them</td>
            </tr>
            <tr>
              <th scope="row">Commander</th>
              <td>See unit posture and roster pressure. No names.</td>
            </tr>
            <tr>
              <th scope="row">Ethics and privacy</th>
              <td>Watch fairness, access, and the line that never reaches posting or appraisal</td>
            </tr>
          </tbody>
        </table>
      </section>
      </main>
    </div>
  );
}
