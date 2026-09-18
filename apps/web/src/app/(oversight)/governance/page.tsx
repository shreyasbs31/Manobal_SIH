"use client";

import {
  AuditRow,
  ChainStatus,
  FairnessBar,
  KpiTile,
  ProviderBadge,
} from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function GovernancePage() {
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("governance", async (client, signal) => {
    const [kpis, fairness, switches, audit, rules, models, providers, reviews, safety] =
      await Promise.all([
        client.govOverview(signal),
        client.govFairness(signal),
        client.govKillswitches(signal),
        client.govAudit(signal),
        client.govRulesets(signal),
        client.govModels(signal),
        client.govProviders(signal),
        client.govReviews(signal),
        client.govAgentSafety(signal),
      ]);
    return { kpis, fairness, switches, audit, rules, models, providers, reviews, safety };
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
        <div className="mb-gov">
          {data.kpis.cost_banner ? (
            <p className="mb-cost-banner" role="status">
              {data.kpis.cost_banner}
            </p>
          ) : null}
          {notice ? (
            <p role="alert">{notice}</p>
          ) : null}
          <div className="mb-kpi-row mb-kpi-row-wide">
            {data.kpis.kpis.map((kpi) => (
              <KpiTile hint={kpi.hint} key={kpi.label} label={kpi.label} value={kpi.value} />
            ))}
          </div>
          <p>Source: {data.kpis.source ?? "core or demo cases"}.</p>
          <div className="mb-grid-12">
            {data.fairness.fairness.map((row) => (
              <div className="mb-span-6" key={row.label}>
                <FairnessBar label={row.label} ratio={row.ratio} />
              </div>
            ))}
            <div className="mb-span-12">
              <p>
                Exposure parity band {data.fairness.band ?? "0.80 to 1.25"}.{" "}
                {data.fairness.note}
              </p>
            </div>
            <div className="mb-span-12 mb-card">
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
                      setNotice(
                        result.valid
                          ? "Chain verified."
                          : "Chain is broken. Restore to heal it.",
                      );
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
                      setNotice("The chain is broken. Restore heals it.");
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
              <AuditRow action="anchor.daily" token="tok_aa19" when="06:00" />
            </div>
            <div className="mb-span-6 mb-card">
              <h2>Kill switches</h2>
              {Object.entries(data.switches).map(([name, enabled]) => (
                <div className="mb-kill" key={name}>
                  <span>{name}</span>
                  <button
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
                <button
                  className="mb-toggle"
                  onClick={() =>
                    void run("acute", async () => {
                      try {
                        await engineClient().setKillswitch("acute");
                      } catch (caught: unknown) {
                        setNotice(
                          caught instanceof Error
                            ? caught.message
                            : "The acute path cannot be switched off",
                        );
                      }
                    })
                  }
                  type="button"
                >
                  Always on
                </button>
              </div>
            </div>
            <div className="mb-span-6 mb-card">
              <h2>Model card</h2>
              <p>{String((data.models as { card?: { name?: string } }).card?.name ?? "lgbm-v1")}</p>
              <p>Trained on the primary synthetic world only. Forecast never places T3 or T4.</p>
              <p>Excluded attributes never enter scoring.</p>
            </div>
            <div className="mb-span-12 mb-card">
              <h2>Ruleset registry</h2>
              <p>
                Active {data.rules.active}. Shadow {data.rules.shadow}. Signers{" "}
                {data.rules.signers.join(" and ")}. Signed {data.rules.signed ? "yes" : "no"}.
              </p>
              <pre className="mb-yaml">{data.rules.yaml.split("\n").slice(0, 16).join("\n")}</pre>
            </div>
            <div className="mb-span-6 mb-card">
              <h2>Provider health</h2>
              <ProviderBadge name="Azure Speech" />
              <ProviderBadge name="Foundry open" />
              <p>
                {String(
                  (data.providers as { foundry_configured?: boolean }).foundry_configured
                    ? "Foundry is configured."
                    : "Foundry unset. Local fallbacks are labelled.",
                )}
              </p>
            </div>
            <div className="mb-span-6 mb-card">
              <h2>Reveal reviews</h2>
              <ul>
                {(data.reviews.items ?? []).map((row) => (
                  <li key={row.id}>
                    {row.kind}: {row.status}. {row.note}
                  </li>
                ))}
              </ul>
              <p>
                Agent safety: crisis fails to crisis. Alt never serves personnel.{" "}
                {String((data.safety as { acute_kill_locked?: boolean }).acute_kill_locked ? "Acute stays on." : "")}
              </p>
            </div>
            <div className="mb-span-12 mb-action-row">
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
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
