"use client";

import { mePrivacy } from "@manobal/contracts";
import { SceneOnboardingPhone } from "@manobal/illustrations";
import {
  AccessLedgerItem,
  BaselineRibbonChart,
  ConsentToggleCard,
  IconHiddenLock,
  IconLeaveWindow,
  IconVaultKey,
  ReceiptCard,
} from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

const ICONS = [IconHiddenLock, IconLeaveWindow, IconVaultKey] as const;

export default function MePage() {
  const { data, error, loading, offline } = useEngine("me", async (client, signal) => {
    const [consents, ledger, trends] = await Promise.all([
      client.meConsents(signal),
      client.meLedger(signal),
      client.meTrends(signal),
    ]);
    return { consents, ledger, trends };
  });
  const [consents, setConsents] = useState<boolean[]>([]);
  const [receipt, setReceipt] = useState(mePrivacy.receipt);
  const items = data?.consents.items ?? [];
  const checked = consents.length ? consents : items.map((item) => item.on);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <h2 className="mb-type-title">Me</h2>
          <div className="mb-me-points">
            {mePrivacy.statements.map((line, index) => {
              const Icon = ICONS[index] ?? IconVaultKey;
              return (
                <p className="mb-me-point" key={line}>
                  <Icon height={22} width={22} />
                  {line}
                </p>
              );
            })}
          </div>
          {items.map((item, index) => (
            <ConsentToggleCard
              checked={checked[index] ?? false}
              illustration={<SceneOnboardingPhone />}
              key={item.title}
              leavesPhone={item.leavesPhone}
              onChange={(next) => {
                const copy = [...checked];
                copy[index] = next;
                setConsents(copy);
              }}
              title={item.title}
              whoCanSee={item.whoCanSee}
            />
          ))}
          <h2 className="mb-section-label">Who viewed my information</h2>
          {data.ledger.items.length === 0 ? (
            <p>No access yet.</p>
          ) : (
            data.ledger.items.map((item, index) => (
              <AccessLedgerItem
                actor={item.actor_label ?? item.actor ?? "Officer"}
                key={`${item.action ?? "access"}-${index}`}
                purpose={item.purpose_code ?? "Care"}
                when={item.at ?? ""}
              />
            ))
          )}
          <ReceiptCard hash={receipt.hash} time={receipt.time} />
          <BaselineRibbonChart
            label="Sleep hours against your usual range"
            takeaway="Your sleep has been below your usual rhythm for 3 nights."
            values={data.trends.points}
            variant="detail"
          />
          <nav aria-label="Rights" className="mb-rights">
            <a href="#download">
              Download my data <span aria-hidden="true">›</span>
            </a>
            <button
              className="mb-ghost"
              onClick={() => {
                void engineClient()
                  .mePurge("wearable")
                  .then((result) => {
                    setReceipt({
                      hash: result.sha256.slice(0, 16),
                      time: result.at,
                    });
                  });
              }}
              type="button"
            >
              Erase my data <span aria-hidden="true">›</span>
            </button>
            <a href="#consents">
              Manage consents <span aria-hidden="true">›</span>
            </a>
          </nav>
        </div>
      ) : null}
    </ScreenState>
  );
}
