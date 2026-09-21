"use client";

import { EscalationLadder, SlaTimer, chimeKindForQueue, playConsoleChime } from "@manobal/ui";
import { useEffect, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function MedicalPage() {
  const { tx } = useConsoleLang();
  const { data, error, loading, offline, reload } = useEngine("medical-acute", (client, signal) =>
    client.medicalAcute(signal),
  );
  const extra = useEngine("medical-referrals", (client, signal) => client.medicalReferrals(signal));
  const items = data ?? [];
  const [picked, setPicked] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const kind = chimeKindForQueue(items.filter((item) => item.tier === "T4").length, 0);
    if (kind) {
      playConsoleChime(kind);
    }
  }, [items]);

  useEffect(() => {
    if (!picked && items[0]) {
      setPicked(items[0].case_id);
    }
  }, [items, picked]);

  const current = items.find((item) => item.case_id === picked) ?? items[0];
  const referral =
    extra.data?.items.find((item) => item.case_id === current?.case_id) ?? extra.data?.items[0];
  const guideSteps = [tx.guideStay, tx.guideReach, tx.guideInvolve, tx.guidePolicy];

  async function openCall() {
    try {
      const result = await engineClient().callsToken();
      setNotice(result.configured ? tx.callReady : tx.callUnavailable);
    } catch {
      setNotice(tx.callUnavailable);
    }
  }

  return (
    <ScreenState
      empty={data === null}
      emptyText={tx.emptyAcute}
      error={error}
      loading={loading}
      loadingText={tx.loading}
      offline={offline}
      offlineText={tx.offlineView}
    >
      <div className="mb-desk mb-acute-desk">
        <p className="mb-desk-purpose">{tx.acutePurpose}</p>
        {notice ? <p className="mb-acute-notice" role="status">{notice}</p> : null}
        {current ? (
          <>
            <section className="mb-acute-hero">
              <div className="mb-acute-hero-copy">
                <span>{tx.acuteCaseOpen}</span>
                <h2>{current.case_id}</h2>
                <p>{tx.acuteImmediate}</p>
              </div>
              <div className="mb-acute-timer">
                <SlaTimer
                  label={tx.acknowledge}
                  remainingLabel={current.sla_label}
                  remainingRatio={current.remaining_ratio}
                  tier="T4"
                />
              </div>
              <dl className="mb-acute-meta">
                <div>
                  <dt>{tx.acuteOpenedAt}</dt>
                  <dd>{referral?.opened ?? "09:41"}</dd>
                </div>
                <div>
                  <dt>{tx.acuteOwner}</dt>
                  <dd>{tx.roleMo}</dd>
                </div>
                <div>
                  <dt>{tx.dpoStatus}</dt>
                  <dd>{current.status === "ack" ? tx.statusAck : tx.acuteAwaiting}</dd>
                </div>
              </dl>
              <div className="mb-acute-hero-actions">
                <button
                  className="mb-primary mb-ack"
                  disabled={current.status === "ack"}
                  onClick={() => {
                    void engineClient()
                      .medicalAck(current.case_id)
                      .then(() => {
                        setNotice(tx.ackDone);
                        reload();
                      });
                  }}
                  type="button"
                >
                  {current.status === "ack" ? tx.ackDone : tx.acknowledge}
                </button>
                <button className="mb-secondary" onClick={() => void openCall()} type="button">
                  {tx.callNow}
                </button>
              </div>
            </section>
            {items.length > 1 ? (
              <nav aria-label={tx.acuteOpen} className="mb-acute-tabs">
                {items.map((item) => (
                  <button
                    aria-pressed={item.case_id === current.case_id}
                    key={item.case_id}
                    onClick={() => setPicked(item.case_id)}
                    type="button"
                  >
                    {item.case_id}
                  </button>
                ))}
              </nav>
            ) : null}
            <div className="mb-acute-workspace">
              <section className="mb-sheet mb-acute-context">
                <h2>{tx.acuteContext}</h2>
                <dl className="mb-fact-list">
                  <div>
                    <dt>{tx.acuteTrigger}</dt>
                    <dd>{tx.acuteTriggerDetail}</dd>
                  </div>
                  <div>
                    <dt>{tx.acuteChannel}</dt>
                    <dd>{tx.acuteSpoken}</dd>
                  </div>
                  <div>
                    <dt>{tx.acuteLanguage}</dt>
                    <dd>{tx.acuteHindiPreferred}</dd>
                  </div>
                  <div>
                    <dt>{tx.acuteLocation}</dt>
                    <dd>{tx.acuteUnitArea}</dd>
                  </div>
                  <div>
                    <dt>{tx.acutePrivacy}</dt>
                    <dd>{tx.acuteNoAssessment}</dd>
                  </div>
                </dl>
              </section>
              <section className="mb-sheet mb-acute-response">
                <h2>{tx.whoReached}</h2>
                <EscalationLadder
                  current={current.status === "ack" ? tx.roleMo : tx.statusWaiting}
                  steps={[
                    { role: tx.roleUwo, status: tx.statusNotified, time: "09:41" },
                    { role: tx.roleDeputy, status: tx.statusWaiting, time: "" },
                    {
                      role: tx.roleMo,
                      status: current.status === "ack" ? tx.statusAck : tx.statusWaiting,
                      time: current.status === "ack" ? tx.now : "",
                    },
                    { role: tx.roleCounsellor, status: tx.statusWaiting, time: "" },
                  ]}
                />
                <p className="mb-acute-last">
                  <strong>{tx.acuteLastAction}</strong>
                  {tx.acuteWelfareNotified}
                </p>
              </section>
              <section className="mb-sheet mb-acute-protocol">
                <h2>{tx.acuteProtocol}</h2>
              <ol className="mb-guide">
                {guideSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
                <p>{tx.guideNote}</p>
              </section>
            </div>
          </>
        ) : (
          <section className="mb-sheet mb-acute-clear">
            <h2>{tx.emptyAcute}</h2>
            <p>{tx.quietAcute}</p>
            <h3>{tx.stayGuide}</h3>
            <ol className="mb-guide">
              {guideSteps.map((step) => <li key={step}>{step}</li>)}
            </ol>
          </section>
        )}
      </div>
    </ScreenState>
  );
}
