"use client";

import {
  AccessLedgerItem,
  BaselineRibbonChart,
  ConsentToggleCard,
  LeaveWindowPicker,
  LimitedDataTag,
  ReceiptCard,
} from "@manobal/ui";

const ribbon = [
  { day: 1, value: 6.2 },
  { day: 15, value: 6.0 },
  { day: 30, value: 5.4 },
  { day: 45, value: 4.8 },
  { day: 60, value: 4.1 },
  { day: 75, value: 3.6 },
  { day: 90, value: 3.4 },
] as const;

export default function MePage() {
  return (
    <div className="mb-home-stack">
      <h1>Me</h1>
      <LimitedDataTag />
      <BaselineRibbonChart label="Sleep hours against your usual range" values={ribbon} />
      <ConsentToggleCard
        checked
        leavesPhone="Encrypted check-in summary only"
        onChange={() => undefined}
        title="Daily check-in"
        whoCanSee="You. A welfare officer only after you agree."
      />
      <LeaveWindowPicker />
      <ReceiptCard hash="sha256:4ab1c0ffee" time="16 Sep 2026, 09:12 IST" />
      <section className="mb-card">
        <h2>Access ledger</h2>
        <AccessLedgerItem
          actor="You"
          purpose="Opened rights centre"
          when="16 Sep 2026"
        />
      </section>
    </div>
  );
}
