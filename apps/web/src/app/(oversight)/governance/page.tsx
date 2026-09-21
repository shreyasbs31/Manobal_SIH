"use client";

import { AuditRow, ChainStatus, FairnessBar, KpiTile } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function GovernancePage() {
  const { tx } = useConsoleLang();
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("governance", async (client, signal) => {
    const [kpis, fairness, switches, audit, rules, reviews] = await Promise.all([
      client.govOverview(signal),
      client.govFairness(signal),
      client.govKillswitches(signal),
      client.govAudit(signal),
      client.govRulesets(signal),
      client.govReviews(signal),
    ]);
    return { kpis, fairness, switches, audit, rules, reviews };
  });

  async function run(label: string, work: () => Promise<void>) {
    setBusy(label);
    setNotice(null);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : tx.couldNotComplete);
    } finally {
      setBusy(null);
    }
  }

  const chainMode = data?.audit.mode as "intact" | "verify" | "tamper" | "heal" | undefined;
  const switchLabel = (name: string) => {
    if (name === "agent") return tx.companion;
    if (name === "voice") return tx.voice;
    if (name === "copilot") return tx.copilot;
    if (name === "briefs") return tx.caseBriefs;
    if (name === "alerts_t2_t3") return tx.alertsT2;
    if (name === "forecast") return tx.forecast;
    if (name === "jitai") return tx.nudges;
    return name;
  };

  return (
    <ScreenState
      error={error}
      loading={loading}
      offline={offline}
      empty={!data}
      loadingText={tx.loading}
      offlineText={tx.offlineView}
    >
      {data ? (
        <div className="mb-gov-desk">
          <p className="mb-desk-purpose">{tx.govPurpose}</p>
          {data.kpis.cost_banner ? (
            <p className="mb-cost-banner" role="status">
              {data.kpis.cost_banner}
            </p>
          ) : null}
          {notice ? (
            <p className="mb-gov-wide" role="alert">
              {notice}
            </p>
          ) : null}
          <section className="mb-sheet mb-gov-snapshot">
            <div className="mb-section-head">
              <div>
                <h2>{tx.govSnapshot}</h2>
                <p>{tx.govSnapshotNote}</p>
              </div>
              <span>{data.kpis.source ?? tx.simulated}</span>
            </div>
            <div className="mb-gov-kpis">
              {data.kpis.kpis.map((kpi) => (
                <KpiTile hint={kpi.hint} key={kpi.label} label={kpi.label} value={kpi.value} />
              ))}
            </div>
          </section>
          <section className="mb-sheet mb-gov-fairness">
            <div className="mb-section-head">
              <div>
                <h2>{tx.govFair}</h2>
                <p>{tx.govFairNote}</p>
              </div>
              <strong>{tx.govFairNoteShort}</strong>
            </div>
            <div className="mb-gov-fair">
              {data.fairness.fairness.map((row) => (
                <FairnessBar key={row.label} label={row.label} ratio={row.ratio} />
              ))}
            </div>
          </section>
          <div className="mb-gov-columns">
            <div className="mb-gov-column">
              <section className="mb-sheet">
                <div className="mb-section-head">
                  <div>
                    <h2>{tx.auditChain}</h2>
                    <p>{tx.govEvidence}</p>
                  </div>
                  <ChainStatus mode={chainMode ?? "intact"} />
                </div>
                <p>
                  {data.audit.valid
                    ? `${tx.verifiedBlocks} ${data.audit.checked}`
                    : `${tx.chainBreak} ${data.audit.broken_seq ?? "?"}.`}
                </p>
                <div className="mb-action-row">
                  <button
                    className="mb-secondary"
                    disabled={busy !== null}
                    onClick={() =>
                      void run("verify", async () => {
                        const result = await engineClient().govAuditVerify();
                        setNotice(result.valid ? tx.chainVerified : tx.chainBroken);
                      })
                    }
                    type="button"
                  >
                    {tx.verify}
                  </button>
                  <button
                    className="mb-ghost"
                    disabled={busy !== null}
                    onClick={() =>
                      void run("tamper", async () => {
                        await engineClient().govAuditTamper();
                        setNotice(tx.chainBroken);
                      })
                    }
                    type="button"
                  >
                    {tx.tamper}
                  </button>
                  <button
                    className="mb-primary"
                    disabled={busy !== null}
                    onClick={() =>
                      void run("restore", async () => {
                        await engineClient().govAuditRestore();
                        setNotice(tx.chainRestored);
                      })
                    }
                    type="button"
                  >
                    {tx.restore}
                  </button>
                </div>
                <AuditRow action={tx.dailySeal} token={tx.intact} when="06:00" />
              </section>
              <section className="mb-sheet">
                <h2>{tx.revealReviews}</h2>
                {(data.reviews.items ?? []).length === 0 ? (
                  <p>{tx.noReviews}</p>
                ) : (
                  (data.reviews.items ?? []).map((row) => {
                    const reviewId = row.id ?? "";
                    if (!reviewId) return null;
                    return (
                      <article className="mb-review-row" key={reviewId}>
                        <div>
                          <strong>{row.kind}</strong>
                          <p>{row.note}</p>
                        </div>
                        {row.status === "open" ? (
                          <div className="mb-action-row">
                            <button
                              className="mb-secondary"
                              disabled={busy !== null}
                              onClick={() =>
                                void run(reviewId, async () => {
                                  await engineClient().govReviewDecide(reviewId, "approved");
                                  setNotice(tx.reviewApproved);
                                })
                              }
                              type="button"
                            >
                              {tx.approve}
                            </button>
                            <button
                              className="mb-ghost"
                              disabled={busy !== null}
                              onClick={() =>
                                void run(`${reviewId}-hold`, async () => {
                                  await engineClient().govReviewDecide(reviewId, "held");
                                  setNotice(tx.reviewHeld);
                                })
                              }
                              type="button"
                            >
                              {tx.holdReview}
                            </button>
                          </div>
                        ) : <span>{row.status}</span>}
                      </article>
                    );
                  })
                )}
                <button
                  className="mb-secondary"
                  disabled={busy !== null}
                  onClick={() =>
                    void run("report", async () => {
                      await engineClient().govTransparency();
                      const blob = await engineClient().govTransparencyPdf();
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement("a");
                      link.href = url;
                      link.download = "transparency.pdf";
                      link.click();
                      URL.revokeObjectURL(url);
                      setNotice(tx.transparencyDownloaded);
                    })
                  }
                  type="button"
                >
                  {tx.downloadTransparency}
                </button>
              </section>
            </div>
            <div className="mb-gov-column">
              <section className="mb-sheet">
                <div className="mb-section-head">
                  <div>
                    <h2>{tx.govSafeguards}</h2>
                    <p>{tx.govSafeguardsNote}</p>
                  </div>
                </div>
                <div className="mb-switch-grid">
                  {Object.entries(data.switches).map(([name, enabled]) => (
                    <div className="mb-switch-cell" key={name}>
                      <span>{switchLabel(name)}</span>
                      <button
                        aria-pressed={enabled}
                        className="mb-toggle"
                        disabled={busy !== null}
                        onClick={() =>
                          void run(name, async () => {
                            await engineClient().setKillswitch(name);
                          })
                        }
                        type="button"
                      >
                        {enabled ? tx.on : tx.off}
                      </button>
                    </div>
                  ))}
                  <div className="mb-switch-cell" data-locked="true">
                    <span>{tx.acutePath}</span>
                    <button className="mb-toggle" onClick={() => setNotice(tx.acuteLocked)} type="button">
                      {tx.alwaysOn}
                    </button>
                  </div>
                </div>
              </section>
              <section className="mb-sheet">
                <div className="mb-section-head">
                  <div>
                    <h2>{tx.govRegistry}</h2>
                    <p>{tx.govRulesNote}</p>
                  </div>
                  <strong>{data.rules.active}</strong>
                </div>
                <details>
                  <summary>{tx.govShowRules}</summary>
                  <pre className="mb-yaml">{data.rules.yaml.split("\n").slice(0, 12).join("\n")}</pre>
                </details>
              </section>
            </div>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
