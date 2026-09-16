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
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

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
  const { data, error, loading, offline, reload } = useEngine(
    `case-${caseId}`,
    (client, signal) => client.welfareCase(caseId, signal) as unknown as Promise<CasePayload>,
  );
  const [purpose, setPurpose] = useState("care_contact");
  const [justification, setJustification] = useState("");
  const [reveal, setReveal] = useState<RevealCard | null>(null);
  const [note, setNote] = useState("");
  const [mode, setMode] = useState("call");
  const [lever, setLever] = useState("REST_48H");
  const [followUp, setFollowUp] = useState("D+2");
  const [refer, setRefer] = useState("");
  const [trend, setTrend] = useState("Sleep, not yet requested");
  const [briefLang, setBriefLang] = useState("hi");
  const [message, setMessage] = useState("");

  const nodes = useMemo(() => (data ? briefNodes(data.brief, data.brief_fields) : []), [data]);

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
              <h2>Trend sharing</h2>
              <p>{trend}</p>
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient()
                    .welfareTrendRequest(caseId, "sleep")
                    .then(() => setTrend("Sleep, request pending"));
                }}
                type="button"
              >
                Request sleep trend
              </button>
            </section>
            <section>
              <h2>Recommended actions</h2>
              {data.levers.map((item, index) => (
                <LeverOption
                  hint={item.hint}
                  index={index + 1}
                  key={item.title}
                  rationale={item.rationale}
                  title={item.title}
                />
              ))}
              <label>
                Brief language
                <select onChange={(event) => setBriefLang(event.target.value)} value={briefLang}>
                  <option value="hi">Hindi</option>
                  <option value="en">English</option>
                </select>
              </label>
              <BriefPanel>
                <p lang={briefLang}>{nodes}</p>
                <p>Openers</p>
                <ol>
                  {(data.openers ?? []).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ol>
              </BriefPanel>
            </section>
            <section>
              <h2>Identity</h2>
              {reveal ? (
                <div className="mb-identity-card">
                  <p>{reveal.notice}</p>
                  <p>
                    {String(reveal.card.label)}. {String(reveal.card.rank)}. {String(reveal.card.unit)}.
                  </p>
                  <p>Contact {String(reveal.card.contact)}. Note due {reveal.contact_note_due}.</p>
                  <label>
                    Contact note
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
                    Save contact note
                  </button>
                </div>
              ) : (
                <>
                  <p>Locked</p>
                  <label>
                    Purpose
                    <select onChange={(event) => setPurpose(event.target.value)} value={purpose}>
                      <option value="care_contact">Care contact</option>
                      <option value="urgent_welfare">Urgent welfare</option>
                      <option value="follow_up">Follow up</option>
                    </select>
                  </label>
                  <label>
                    Why you need to reach them
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
                        })
                        .catch((caught: unknown) => {
                          setMessage(caught instanceof Error ? caught.message : "Reveal failed");
                        });
                    }}
                    type="button"
                  >
                    Reveal to contact
                  </button>
                  <p>This person will see that you viewed it.</p>
                </>
              )}
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
              <label>
                Contacted
                <select onChange={(event) => setMode(event.target.value)} value={mode}>
                  <option value="call">Call</option>
                  <option value="visit">Visit</option>
                  <option value="message">Message</option>
                </select>
              </label>
              <label>
                Decision
                <select onChange={(event) => setLever(event.target.value)} value={lever}>
                  <option value="REST_48H">48-hour rest</option>
                  <option value="NO_ACTION">No action needed</option>
                  <option value="COUNSELLOR_REFERRAL">Refer to counsellor</option>
                </select>
              </label>
              <label>
                Follow-up
                <input onChange={(event) => setFollowUp(event.target.value)} value={followUp} />
              </label>
              <label>
                Refer
                <select onChange={(event) => setRefer(event.target.value)} value={refer}>
                  <option value="">None</option>
                  <option value="counsellor">Counsellor</option>
                  <option value="mo">Medical officer</option>
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
                Record action
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
                Close case
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
