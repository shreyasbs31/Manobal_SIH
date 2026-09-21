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
import { usePersonnelI18n } from "@/lib/personnel-i18n";
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
  const { p } = usePersonnelI18n();
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
                copy={{
                  usualRange: p("Your usual range"),
                  dataTable: p("Data table"),
                  day: p("Day"),
                  value: p("Value"),
                  outsideRange: p("is outside the usual range"),
                }}
                label={p("Your mood and sleep against your usual range")}
                takeaway={p(data.takeaway)}
                values={[...data.ribbon]}
                variant="hero"
              />
            </div>
          ) : (
            <h1 className="mb-type-title">{p("Saathi")}</h1>
          )}
          {data ? (
            <article className="mb-checkin-card">
              <div>
                <h2>{p(data.checkin.title)}</h2>
                <p>
                  {data.checkin.done
                    ? p("Done for today")
                    : p("{n} seconds", { n: data.checkin.duration_s })}
                </p>
              </div>
              <Link className="mb-primary" href={data.checkin.href}>
                {p(data.checkin.done ? "Open" : "Start")}
              </Link>
            </article>
          ) : (
            <article className="mb-checkin-card">
              <div>
                <h2>{p("Daily check-in")}</h2>
                <p>{p("Works on this phone without a network.")}</p>
              </div>
              <Link className="mb-primary" href="/app/check-in">
                {p("Start")}
              </Link>
            </article>
          )}
          <p className="mb-section-label">{p("For you now")}</p>
          {cards.map((card) => (
            <article className="mb-context-card" key={card.title}>
              {illustrationFor("kind" in card && typeof card.kind === "string" ? card.kind : "nudge")}
              <div>
                <h2>{p(card.title)}</h2>
                <p>{p(card.detail)}</p>
                <p className="mb-why">{p("Why this? {text}", { text: p(card.why) })}</p>
              </div>
            </article>
          ))}
          {offline
            ? local.map((card) => (
                <article className="mb-context-card" key={card.title}>
                  <SceneSleepWindDown />
                  <div>
                    <h2>{p(card.title)}</h2>
                    <p className="mb-why">{p("Why this? {text}", { text: p(card.why) })}</p>
                  </div>
                </article>
              ))
            : null}
          <nav aria-label={p("Shortcuts")} className="mb-quick-tiles">
            {TILES.map((tile) => {
              const Icon = tile.icon;
              return (
                <Link href={tile.href} key={tile.href}>
                  <Icon height={22} width={22} />
                  {p(tile.label)}
                </Link>
              );
            })}
          </nav>
        </div>
      ) : null}
    </ScreenState>
  );
}
