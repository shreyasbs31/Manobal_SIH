"use client";

import {
  BaselineRibbonChart,
  ContourTexture,
  IconLeaveWindow,
  IconShiftMoon,
  IconVoiceContour,
} from "@manobal/ui";
import { SceneSleepWindDown } from "@manobal/illustrations";
import Link from "next/link";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function SaathiHomePage() {
  const { data, error, loading, offline } = useEngine("home", (client, signal) =>
    client.meHome(signal),
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <div className="mb-ribbon-hero">
            <ContourTexture height={140} seed={data.persona_id} width={390} />
            <BaselineRibbonChart
              label="Your mood and sleep against your usual range"
              takeaway={data.takeaway}
              values={[...data.ribbon]}
              variant="hero"
            />
          </div>
          <article className="mb-checkin-card">
            <div>
              <h2>{data.checkin.title}</h2>
              <p>{data.checkin.duration_s} seconds</p>
            </div>
            <Link className="mb-primary" href={data.checkin.href}>
              Start
            </Link>
          </article>
          <p className="mb-section-label">For you now</p>
          <article className="mb-context-card">
            <SceneSleepWindDown />
            <div>
              <h2>{data.nudge.title}</h2>
              <p>{data.nudge.detail}</p>
              <p>Why this? {data.nudge.why}</p>
            </div>
          </article>
          <nav aria-label="Shortcuts" className="mb-quick-tiles">
            <Link href="/app/saathi">
              <IconVoiceContour height={22} width={22} />
              Talk
            </Link>
            <Link href="/app/toolkit/breathe">
              <IconShiftMoon height={22} width={22} />
              Breathe
            </Link>
            <Link href="/app/saathi">
              <IconVoiceContour height={22} width={22} />
              Counsellor
            </Link>
            <Link href="/app/me">
              <IconLeaveWindow height={22} width={22} />
              Leave
            </Link>
          </nav>
        </div>
      ) : null}
    </ScreenState>
  );
}
