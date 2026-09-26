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
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

const ICONS = [IconHiddenLock, IconLeaveWindow, IconVaultKey] as const;

function formatAccessWhen(value: string, lang: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const locale = lang === "hi" ? "hi-IN" : lang === "ta" ? "ta-IN" : "en-GB";
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function MePage() {
  const { lang, p } = usePersonnelI18n();
  const { data, error, loading, offline, reload } = useEngine("me", async (client, signal) => {
    const [consents, ledger, trends, rights, remembers] = await Promise.all([
      client.meConsents(signal),
      client.meLedger(signal),
      client.meTrends(signal),
      client.meRights(signal),
      client.meRemembers(signal),
    ]);
    return { consents, ledger, trends, rights, remembers };
  });
  const [consents, setConsents] = useState<boolean[]>([]);
  const [receipt, setReceipt] = useState(mePrivacy.receipt);
  const [simple, setSimple] = useState(
    typeof window === "undefined" ? false : window.localStorage.getItem("manobal.simple_mode") === "1",
  );
  const [pulseNote, setPulseNote] = useState("");
  const items = data?.consents.items ?? [];
  const checked = consents.length ? consents : items.map((item) => item.on);
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    let channel: BroadcastChannel | null = null;
    try {
      channel = new BroadcastChannel("manobal-ledger");
      channel.addEventListener("message", () => reloadRef.current());
    } catch {
      channel = null;
    }
    const timer = window.setInterval(() => reloadRef.current(), 2500);
    return () => {
      channel?.close();
      window.clearInterval(timer);
    };
  }, []);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data && !offline}>
      {data || offline ? (
        <div className="mb-home-stack">
          <div className="mb-me-points">
            {mePrivacy.statements.map((line, index) => {
              const Icon = ICONS[index] ?? IconVaultKey;
              return (
                <p className="mb-me-point" key={line}>
                  <Icon height={22} width={22} />
                  {p(line)}
                </p>
              );
            })}
          </div>
          <h2 className="mb-section-label">{p("My trends")}</h2>
          {data ? (
            <BaselineRibbonChart
              copy={{
                usualRange: p("Your usual range"),
                dataTable: p("Data table"),
                day: p("Day"),
                value: p("Value"),
                outsideRange: p("is outside the usual range"),
              }}
              label={p("Sleep hours against your usual range")}
              takeaway={p("Your sleep has been below your usual rhythm for 3 nights.")}
              values={data.trends.points}
              variant="detail"
            />
          ) : (
            <p>{p("Your last saved sleep and mood stay on this phone.")}</p>
          )}

          {items.map((item, index) => (
            <ConsentToggleCard
              checked={checked[index] ?? false}
              copy={{
                leavesPhone: p("What leaves your phone"),
                whoCanSee: p("Who can ever see this"),
                on: p("On"),
                off: p("Off"),
              }}
              illustration={<SceneOnboardingPhone />}
              key={item.title}
              leavesPhone={p(item.leavesPhone)}
              onChange={(next) => {
                const copy = [...checked];
                copy[index] = next;
                setConsents(copy);
              }}
              title={p(item.title)}
              whoCanSee={p(item.whoCanSee)}
            />
          ))}

          <h2 className="mb-section-label">{p("Who viewed my information")}</h2>
          {data && data.ledger.items.length === 0 ? (
            <p>{p("No access yet.")}</p>
          ) : data ? (
            data.ledger.items.map((item, index) => (
              <AccessLedgerItem
                actor={
                  item.action === "identity.viewed"
                    ? p(item.actor_label ?? "Welfare Officer, your unit, viewed your identity")
                    : p(item.actor_label ?? item.actor ?? "Officer")
                }
                key={`${item.action ?? "access"}-${index}`}
                purpose={
                  item.action === "identity.viewed"
                    ? p("Care contact")
                    : p(item.purpose_code ?? "Care")
                }
                when={formatAccessWhen(item.at ?? "", lang)}
              />
            ))
          ) : (
            <p>{p("Saved on this phone. Officers cannot see this list while you are offline.")}</p>
          )}
          <ReceiptCard
            copy={{ title: p("Consent receipt"), download: p("Download") }}
            hash={receipt.hash}
            time={receipt.time}
          />

          <nav aria-label={p("Your choices")} className="mb-rights">
            <Link href="/trust">
              {p("Privacy notice")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/talk">
              {p("Talk to a person")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/concerns">
              {p("Raise a concern")} <span aria-hidden="true">›</span>
            </Link>
            <button
              className="mb-ghost"
              onClick={() => {
                void engineClient()
                  .eraseRights("self_report")
                  .then((result) => {
                    setReceipt({
                      hash: result.sha256.slice(0, 16),
                      time: result.at,
                    });
                  });
              }}
              type="button"
            >
              {p("Erase my data")} <span aria-hidden="true">›</span>
            </button>
          </nav>

          <h2 className="mb-section-label">{p("This week")}</h2>
          <p>{p("Your name is not attached.")}</p>
          <div className="mb-action-row">
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .savePulse("unit", 1)
                  .then(() => setPulseNote(p("Saved.")));
              }}
              type="button"
            >
              {p("This week felt heavy")}
            </button>
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .savePulse("unit", 0)
                  .then(() => setPulseNote(p("Saved.")));
              }}
              type="button"
            >
              {p("This week felt steady")}
            </button>
          </div>
          <p>{p("I believe this app is here to support me.")}</p>
          <div className="mb-action-row">
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .savePulse("trust", 1)
                  .then(() => setPulseNote(p("Saved.")));
              }}
              type="button"
            >
              {p("Yes")}
            </button>
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .savePulse("trust", 0)
                  .then(() => setPulseNote(p("Saved.")));
              }}
              type="button"
            >
              {p("Not yet")}
            </button>
          </div>
          {pulseNote ? <p>{pulseNote}</p> : null}

          <h2 className="mb-section-label">{p("What Saathi remembers")}</h2>
          <p>{p("Off unless you turn it on. Officers never see this.")}</p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .saveRemembers({ opt_in: !(data?.remembers.opt_in ?? false) })
                .then(() => reload());
            }}
            type="button"
          >
            {p((data?.remembers.opt_in ?? false) ? "Turn off remembering" : "Turn on remembering")}
          </button>
          {(data?.remembers.items ?? []).map((item) => (
            <p key={item.text}>{p(item.text)}</p>
          ))}
          <button
            className="mb-ghost"
            onClick={() => {
              void engineClient().saveRemembers({ forget: true }).then(() => reload());
            }}
            type="button"
          >
            {p("Forget everything")}
          </button>

          <h2 className="mb-section-label">{p("Settings")}</h2>
          <label className="mb-check-row">
            <input
              checked={simple}
              onChange={(event) => {
                setSimple(event.target.checked);
                window.localStorage.setItem("manobal.simple_mode", event.target.checked ? "1" : "0");
                void engineClient().savePersonalisation({ simple_mode: event.target.checked });
              }}
              type="checkbox"
            />
            {p("Simple mode, larger buttons")}
          </label>
          <nav aria-label={p("More on this phone")} className="mb-rights">
            <Link href="/app/plan">
              {p("My safety plan")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/buddy">
              {p("Buddy")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/family">
              {p("Family connect")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/rest">
              {p("Plan my rest")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/assessments">
              {p("Assessments")} <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/onboarding">
              {p("Review consent")} <span aria-hidden="true">›</span>
            </Link>
          </nav>
        </div>
      ) : null}
    </ScreenState>
  );
}
