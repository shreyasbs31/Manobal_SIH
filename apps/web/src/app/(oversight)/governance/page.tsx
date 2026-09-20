"use client";

import {
  AuditRow,
  ChainStatus,
  FairnessBar,
  KpiTile,
} from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

const SWITCH_LABELS: Record<string, string> = {
  agent: "Companion",
  voice: "Voice",
  copilot: "Copilot",
  briefs: "Case briefs",
  alerts_t2_t3: "T2 and T3 alerts",
  forecast: "Forecast",
  jitai: "Nudges",
};

export default function GovernancePage() {
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
      setNotice(caught instanceof Error ? caught.message : "Could not complete that action.");
    } finally {
      setBusy(null);
    }
  }

  const chainMode = data?.audit.mode as "intact" | "verify" | "tamper" | "heal" | undefined;

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-gov-desk">
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
          <div className="mb-kpi-row mb-kpi-row-wide">
            {data.kpis.kpis.map((kpi) => (
              <KpiTile hint={kpi.hint} key={kpi.label} label={kpi.label} value={kpi.value} />
            ))}
          </div>
          <div className="mb-gov-fair">
            {data.fairness.fairness.map((row) => (
              <FairnessBar key={row.label} label={row.label} ratio={row.ratio} />
            ))}
          </div>
          <section className="mb-sheet">
            <h2>Audit chain</h2>
            <ChainStatus mode={chainMode ?? "intact"} />
            <p>
              {data.audit.valid
                ? `Verified ${data.audit.checked} blocks.`
                : `Break at sequence ${data.audit.broken_seq ?? "?"}.`}
            </p>
            <div className="mb-action-row">
              <button
                className="mb-secondary"
                disabled={busy !== null}
                onClick={() =>
                  void run("verify", async () => {
                    const result = await engineClient().govAuditVerify();
                    setNotice(result.valid ? "Chain verified." : "Chain is broken.");
                  })
                }
                type="button"
              >
                Verify
              </button>
              <button
                className="mb-secondary"
                disabled={busy !== null}
                onClick={() =>
                  void run("tamper", async () => {
                    await engineClient().govAuditTamper();
                    setNotice("Chain broken.");
                  })
                }
                type="button"
              >
                Tamper
              </button>
              <button
                className="mb-primary"
                disabled={busy !== null}
                onClick={() =>
                  void run("restore", async () => {
                    await engineClient().govAuditRestore();
                    setNotice("Chain restored.");
                  })
                }
                type="button"
              >
                Restore
              </button>
            </div>
            <AuditRow action="Daily seal" token="intact" when="06:00" />
          </section>
          <section className="mb-sheet">
            <h2>Kill switches</h2>
            {Object.entries(data.switches).map(([name, enabled]) => (
              <div className="mb-kill" key={name}>
                <span>{SWITCH_LABELS[name] ?? name}</span>
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
                  {enabled ? "On" : "Off"}
                </button>
              </div>
            ))}
            <div className="mb-kill" data-locked="true">
              <span>Acute path</span>
              <button className="mb-toggle" disabled type="button">
                Always on
              </button>
            </div>
          </section>
          <section className="mb-sheet">
            <h2>Reveal reviews</h2>
            {(data.reviews.items ?? []).length === 0 ? (
              <p>No open reviews.</p>
            ) : (
              (data.reviews.items ?? []).map((row) => {
                const reviewId = row.id ?? "";
                if (!reviewId) {
                  return null;
                }
                return (
                  <article className="mb-compare-band" key={reviewId}>
                    <span>
                      {row.kind}: {row.status}
                    </span>
                    <em>{row.note}</em>
                    {row.status === "open" ? (
                      <span className="mb-action-row">
                        <button
                          className="mb-secondary"
                          disabled={busy !== null}
                          onClick={() =>
                            void run(reviewId, async () => {
                              await engineClient().govReviewDecide(reviewId, "approved");
                              setNotice("Review approved.");
                            })
                          }
                          type="button"
                        >
                          Approve
                        </button>
                        <button
                          className="mb-ghost"
                          disabled={busy !== null}
                          onClick={() =>
                            void run(`${reviewId}-hold`, async () => {
                              await engineClient().govReviewDecide(reviewId, "held");
                              setNotice("Review held.");
                            })
                          }
                          type="button"
                        >
                          Hold
                        </button>
                      </span>
                    ) : null}
                  </article>
                );
              })
            )}
            <div className="mb-action-row">
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
                    setNotice("Transparency note downloaded.");
                  })
                }
                type="button"
              >
                Download transparency note
              </button>
            </div>
          </section>
          <section className="mb-sheet">
            <h2>Ruleset {data.rules.active}</h2>
            <pre className="mb-yaml">{data.rules.yaml.split("\n").slice(0, 12).join("\n")}</pre>
          </section>
        </div>
      ) : null}
    </ScreenState>
  );
}
