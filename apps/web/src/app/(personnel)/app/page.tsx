"use client";

import {
  BaselineRibbonChart,
  ContourTexture,
  IconBuddyPair,
  IconLeaveWindow,
  IconShiftMoon,
  IconVoiceContour,
} from "@manobal/ui";
import {
  SceneLeaveWindow,
  SceneShiftMoon,
  SceneSleepWindDown,
} from "@manobal/illustrations";
import Link from "next/link";
import type { ReactNode } from "react";

import { ScreenState } from "@/components/screen-state";
import { localNudgeRules } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";

function illustrationFor(kind: string): ReactNode {
  if (kind === "leave") {
    return <SceneLeaveWindow />;
  }
  if (kind === "lifecycle") {
    return <SceneShiftMoon />;
  }
  return <SceneSleepWindDown />;
}

const TILES = [
  { href: "/app/saathi", label: "Talk", icon: IconVoiceContour },
  { href: "/app/toolkit/breathe", label: "Breathe", icon: IconShiftMoon },
  { href: "/app/talk", label: "Counsellor", icon: IconBuddyPair },
  { href: "/app/rest", label: "Leave", icon: IconLeaveWindow },
] as const;

export default function SaathiHomePage() {
  const { data, error, loading, offline } = useEngine("home", (client, signal) =>
    client.meHome(signal),
  );
  const cards = (data?.context_cards ?? (data ? [data.nudge] : [])).slice(0, 2);
  const local = localNudgeRules({
    sleepNightsLow: offline || data?.persona === "arjun" ? 3 : 0,
    consecutiveDuty: offline || data?.persona === "arjun" ? 11 : 0,
  });

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data && !offline}>
      {data || offline ? (
        <div className="mb-home-stack">
          {data ? (
            <div className="mb-ribbon-hero">
              <ContourTexture height={180} seed={data.persona_id} width={390} />
              <BaselineRibbonChart
                label="Your mood and sleep against your usual range"
                takeaway={data.takeaway}
                values={[...data.ribbon]}
                variant="hero"
              />
            </div>
          ) : (
            <h1 className="mb-type-title">Saathi</h1>
          )}
          {data ? (
            <article className="mb-checkin-card">
              <div>
                <h2>{data.checkin.title}</h2>
                <p>{data.checkin.done ? "Done for today" : `${data.checkin.duration_s} seconds`}</p>
              </div>
              <Link className="mb-primary" href={data.checkin.href}>
                {data.checkin.done ? "Open" : "Start"}
              </Link>
            </article>
          ) : (
            <article className="mb-checkin-card">
              <div>
                <h2>Daily check-in</h2>
                <p>Works on this phone without a network.</p>
              </div>
              <Link className="mb-primary" href="/app/check-in">
                Start
              </Link>
            </article>
          )}
          <p className="mb-section-label">For you now</p>
          {cards.map((card) => (
            <article className="mb-context-card" key={card.title}>
              {illustrationFor("kind" in card && typeof card.kind === "string" ? card.kind : "nudge")}
              <div>
                <h2>{card.title}</h2>
                <p>{card.detail}</p>
                <p className="mb-why">Why this? {card.why}</p>
              </div>
            </article>
          ))}
          {offline
            ? local.map((card) => (
                <article className="mb-context-card" key={card.title}>
                  <SceneSleepWindDown />
                  <div>
                    <h2>{card.title}</h2>
                    <p className="mb-why">Why this? {card.why}</p>
                  </div>
                </article>
              ))
            : null}
          <nav aria-label="Shortcuts" className="mb-quick-tiles">
            {TILES.map((tile) => {
              const Icon = tile.icon;
              return (
                <Link href={tile.href} key={tile.href}>
                  <Icon height={22} width={22} />
                  {tile.label}
                </Link>
              );
            })}
          </nav>
          <p className="mb-status-strip">
            Wearable {data?.status?.wearable ?? "off"}
            {data?.status?.last_sync ? ` · Last sync saved` : null}
          </p>
          <p>
            Home is your rhythm and what to do next. Check in, then pick Talk, Breathe, a counsellor,
            or leave. Assessments and concerns live under Me.
          </p>
        </div>
      ) : null}
    </ScreenState>
  );
}
