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
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";
import { announceWorld } from "@/lib/world";

interface CasePayload {
  case_id: string;
  tier: FixtureTier;
  trajectory: FixtureTrajectory;
  drivers: string[];
  levers: { title: string; hint: string; rationale: string; code?: string }[];
  what_changed: { title: string; detail: string }[];
  brief: string;
  brief_fields: Record<string, string>;
  openers: string[];
  strip: { day: number; tier: FixtureTier }[];
  onset_day: number;
  incidents: number[];
  actions: number[];
  sla_label: string;
  remaining_ratio: number;
}

interface RevealCard {
  revealed: boolean;
  grant_id: string;
  contact_note_due: string;
  notice: string;
  card: Record<string, string | boolean>;
}

export default function CaseWorkspacePage() {
  const params = useParams<{ caseId: string }>();
  const caseId = params.caseId;
  const { lang, tx } = useConsoleLang();
  const { data, error, loading, offline, reload } = useEngine(
    `case-${caseId}-${lang}`,
    (client, signal) =>
      client.welfareCase(caseId, lang, signal) as unknown as Promise<CasePayload>,
  );
  const [purpose, setPurpose] = useState("care_contact");
  const [justification, setJustification] = useState("");
  const [reveal, setReveal] = useState<RevealCard | null>(null);
  const [note, setNote] = useState("");
  const [mode, setMode] = useState("call");
  const [lever, setLever] = useState("REST_48H");
  const [followUp, setFollowUp] = useState("D+2");
  const [refer, setRefer] = useState("");
  const [trend, setTrend] = useState("");
  const [message, setMessage] = useState("");

  const nodes = useMemo(() => (data ? briefNodes(data.brief, data.brief_fields) : []), [data]);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-case-work">
          <header className="mb-action-row">
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
              <h2>{tx.whatChanged}</h2>
              {data.what_changed.map((row) => (
                <p key={row.title}>
                  <strong>{row.title}</strong>
                  <br />
                  {row.detail}
                </p>
              ))}
              <h2>{tx.trendSharing}</h2>
              <p>{trend || tx.trendSleep}</p>
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient()
                    .welfareTrendRequest(caseId, "sleep")
                    .then(() => setTrend(tx.trendPending));
                }}
                type="button"
              >
                {tx.requestSleep}
              </button>
            </section>
            <section>
              <h2>{tx.recommendedActions}</h2>
              {data.levers.map((item, index) => (
                <LeverOption
                  hint={item.hint}
                  index={index + 1}
                  key={item.title}
                  rationale={item.rationale}
                  title={item.title}
                />
              ))}
              <BriefPanel>
                <p lang={lang}>{nodes}</p>
                <p>{tx.waysToOpen}</p>
                <ol>
                  {(data.openers ?? []).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ol>
              </BriefPanel>
            </section>
            <section>
              <h2>{tx.identity}</h2>
              {reveal ? (
                <div className="mb-identity-card">
                  <p>{reveal.notice}</p>
                  <p>
                    {String(reveal.card.label)}. {String(reveal.card.rank)}. {String(reveal.card.unit)}.
                  </p>
                  <p>Contact {String(reveal.card.contact)}. Note due {reveal.contact_note_due}.</p>
                  <label>
                    {tx.contactNote}
                    <textarea onChange={(event) => setNote(event.target.value)} value={note} />
                  </label>
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      void engineClient()
                        .welfareContactNote(reveal.grant_id, note)
                        .then(() => setMessage("Contact note saved."));
                    }}
                    type="button"
                  >
                    {tx.saveNote}
                  </button>
                </div>
              ) : (
                <>
                  <p>{tx.identityLocked}</p>
                  <label>
                    {tx.purpose}
                    <select onChange={(event) => setPurpose(event.target.value)} value={purpose}>
                      <option value="care_contact">{tx.careContact}</option>
                      <option value="urgent_welfare">{tx.urgentWelfare}</option>
                      <option value="follow_up">{tx.followUp}</option>
                    </select>
                  </label>
                  <label>
                    {tx.whyReach}
                    <textarea
                      onChange={(event) => setJustification(event.target.value)}
                      value={justification}
                    />
                  </label>
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      void engineClient()
                        .welfareReveal(caseId, {
                          purpose_code: purpose,
                          justification,
                        })
                        .then((payload) => {
                          setReveal(payload);
                          try {
                            new BroadcastChannel("manobal-ledger").postMessage({
                              caseId,
                              action: "identity.viewed",
                            });
                          } catch {
                            // BroadcastChannel is optional in older webviews.
                          }
                          announceWorld("ledger");
                        })
                        .catch((caught: unknown) => {
                          setMessage(caught instanceof Error ? caught.message : "Reveal failed");
                        });
                    }}
                    type="button"
                  >
                    {tx.revealContact}
                  </button>
                  <p>{tx.viewedNotice}</p>
                </>
              )}
              <h2>{tx.log}</h2>
              <EscalationLadder
                current="waiting"
                steps={[
                  { role: "UWO", status: "acknowledged", time: "09:12" },
                  { role: "Company welfare deputy", status: "notified", time: "09:18" },
                  { role: "Battalion MO", status: "waiting", time: "" },
                  { role: "Sector counsellor", status: "waiting", time: "" },
                ]}
              />
              <label>
                {tx.contacted}
                <select onChange={(event) => setMode(event.target.value)} value={mode}>
                  <option value="call">{tx.call}</option>
                  <option value="visit">{tx.visit}</option>
                  <option value="message">{tx.message}</option>
                </select>
              </label>
              <label>
                {tx.decision}
                <select onChange={(event) => setLever(event.target.value)} value={lever}>
                  <option value="REST_48H">{tx.rest48}</option>
                  <option value="NO_ACTION">{tx.noAction}</option>
                  <option value="COUNSELLOR_REFERRAL">{tx.referCounsellor}</option>
                </select>
              </label>
              <label>
                {tx.followUpField}
                <input onChange={(event) => setFollowUp(event.target.value)} value={followUp} />
              </label>
              <label>
                {tx.refer}
                <select onChange={(event) => setRefer(event.target.value)} value={refer}>
                  <option value="">{tx.none}</option>
                  <option value="counsellor">{tx.counsellor}</option>
                  <option value="mo">{tx.medicalOfficer}</option>
                </select>
              </label>
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient()
                    .welfareAction(caseId, {
                      mode,
                      lever,
                      outcome: "open",
                      follow_up: followUp,
                      refer,
                    })
                    .then(() => {
                      setMessage("Action recorded.");
                      reload();
                    });
                }}
                type="button"
              >
                {tx.recordAction}
              </button>
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient()
                    .welfareAction(caseId, {
                      mode,
                      lever,
                      outcome: "closed",
                      follow_up: followUp,
                      refer,
                    })
                    .then(() => setMessage("Case closed."));
                }}
                type="button"
              >
                {tx.closeCase}
              </button>
              {message ? <p role="status">{message}</p> : null}
            </section>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}

function briefNodes(brief: string, fields: Record<string, string>) {
  const parts = brief.split(/(\[[a-z_]+\])/g);
  return parts.map((part, index) => {
    const match = /^\[([a-z_]+)\]$/.exec(part);
    if (!match) {
      return <span key={`${part}-${index}`}>{part}</span>;
    }
    const key = match[1] ?? "";
    return (
      <abbr className="mb-brief-ref" key={`${key}-${index}`} title={fields[key] ?? key}>
        {part}
      </abbr>
    );
  });
}
