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

const ICONS = [IconHiddenLock, IconLeaveWindow, IconVaultKey] as const;

export default function MePage() {
  const [consents, setConsents] = useState(mePrivacy.consents.map((item) => item.on));

  return (
    <div className="mb-home-stack">
      <h1 className="mb-type-title">Me</h1>
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
      {mePrivacy.consents.map((item, index) => (
        <ConsentToggleCard
          checked={consents[index] ?? false}
          illustration={<SceneOnboardingPhone />}
          key={item.title}
          leavesPhone={item.leavesPhone}
          onChange={(next) => {
            const copy = [...consents];
            copy[index] = next;
            setConsents(copy);
          }}
          title={item.title}
          whoCanSee={item.whoCanSee}
        />
      ))}
      <h2 className="mb-section-label">Who viewed my information</h2>
      {mePrivacy.ledger.map((group) => (
        <section key={group.month}>
          <h3>{group.month}</h3>
          {group.items.map((item) => (
            <AccessLedgerItem
              actor={item.actor}
              key={`${item.actor}-${item.when}`}
              purpose={item.purpose}
              when={item.when}
            />
          ))}
        </section>
      ))}
      <ReceiptCard hash={mePrivacy.receipt.hash} time={mePrivacy.receipt.time} />
      <BaselineRibbonChart
        label="Sleep hours against your usual range"
        takeaway="Your sleep has been below your usual rhythm for 3 nights."
        values={mePrivacy.sleep_ribbon}
        variant="detail"
      />
      <nav aria-label="Rights" className="mb-rights">
        <a href="#download">
          Download my data <span aria-hidden="true">›</span>
        </a>
        <a href="#erase">
          Erase my data <span aria-hidden="true">›</span>
        </a>
        <a href="#consents">
          Manage consents <span aria-hidden="true">›</span>
        </a>
      </nav>
    </div>
  );
}
