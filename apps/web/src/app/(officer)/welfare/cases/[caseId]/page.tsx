"use client";

import {
  BriefPanel,
  CaseStrip,
  EscalationLadder,
  LeverOption,
  SlaTimer,
  TierBadge,
  TrajectoryArrow,
} from "@manobal/ui";
import type { FixtureTier, FixtureTrajectory } from "@manobal/contracts";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

interface CasePayload {
  case_id: string;
  tier: FixtureTier;
  trajectory: FixtureTrajectory;
  drivers: string[];
  levers: { title: string; hint: string; rationale: string }[];
  what_changed: { title: string; detail: string }[];
  brief: string;
  strip: { day: number; tier: FixtureTier }[];
  onset_day: number;
  incidents: number[];
  actions: number[];
  sla_label: string;
  remaining_ratio: number;
}

export default function CaseWorkspacePage() {
  const params = useParams<{ caseId: string }>();
  const caseId = params.caseId;
  const { data, error, loading, offline } = useEngine(`case-${caseId}`, (client, signal) =>
    client.welfareCase(caseId, signal) as unknown as Promise<CasePayload>,
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-case-work">
          <header className="mb-action-row">
            <Link className="mb-ghost" href="/welfare">
              Queue
            </Link>
            <strong>{data.case_id}</strong>
            <TierBadge tier={data.tier} />
            <TrajectoryArrow direction={data.trajectory} />
            <SlaTimer
              label="SLA"
              remainingLabel={data.sla_label}
              remainingRatio={data.remaining_ratio}
              tier={data.tier}
            />
          </header>
          <CaseStrip
            actions={data.actions}
            days={data.strip}
            incidents={data.incidents}
            onsetDay={data.onset_day}
          />
          <div className="mb-case-cols">
            <section>
              <h2>What changed</h2>
              {data.what_changed.map((row) => (
                <p key={row.title}>
                  <strong>{row.title}</strong>
                  <br />
                  {row.detail}
                </p>
              ))}
              <p>Trend sharing: Sleep, request pending.</p>
            </section>
            <section>
              <h2>Recommended actions</h2>
              {data.levers.map((lever, index) => (
                <LeverOption
                  hint={lever.hint}
                  index={index + 1}
                  key={lever.title}
                  rationale={lever.rationale}
                  title={lever.title}
                />
              ))}
              <BriefPanel>
                <p lang="hi">{data.brief}</p>
              </BriefPanel>
            </section>
            <section>
              <h2>Identity</h2>
              <p>Locked</p>
              <button className="mb-secondary" type="button">
                Reveal to contact
              </button>
              <p>This person will see that you viewed it.</p>
              <h2>Log</h2>
              <EscalationLadder
                current="waiting"
                steps={[
                  { role: "UWO", status: "acknowledged", time: "09:12" },
                  { role: "Company welfare deputy", status: "notified", time: "09:18" },
                  { role: "Battalion MO", status: "waiting", time: "" },
                  { role: "Sector counsellor", status: "waiting", time: "" },
                ]}
              />
              <button className="mb-secondary" type="button">
                Close case
              </button>
            </section>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
