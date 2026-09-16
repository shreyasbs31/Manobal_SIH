import { landingRibbon, psMapping } from "@manobal/contracts";
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
    detail: "How the zones stay apart",
    Scene: SceneEmptyPath,
  },
] as const;

export default function LandingPage() {
  return (
    <div className="mb-theme mb-landing" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
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
      <section className="mb-mapping">
        <h2>How the problem statement maps to screens</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">PS component</th>
              <th scope="col">Where it is</th>
            </tr>
          </thead>
          <tbody>
            {psMapping.map(([component, where]) => (
              <tr key={component}>
                <th scope="row">{component}</th>
                <td>{where}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
