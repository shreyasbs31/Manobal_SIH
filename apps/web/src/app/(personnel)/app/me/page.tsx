"use client";

import { t } from "@manobal/i18n";
import { mePrivacy } from "@manobal/contracts";
import { SceneOnboardingPhone } from "@manobal/illustrations";
import {
  AccessLedgerItem,
  BaselineRibbonChart,
  ConsentToggleCard,
  IconHiddenLock,
  IconLeaveWindow,
  IconVaultKey,
  MachineTranslatedBadge,
  ReceiptCard,
} from "@manobal/ui";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

const ICONS = [IconHiddenLock, IconLeaveWindow, IconVaultKey] as const;

export default function MePage() {
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
  const [lang, setLang] = useState(
    typeof window === "undefined" ? "en" : window.localStorage.getItem("manobal.language") ?? "en",
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
          <p>{t("privacy.commander", lang === "hi" || lang === "ta" ? lang : "en")}</p>
          {lang !== "en" && lang !== "hi" && lang !== "ta" ? <MachineTranslatedBadge /> : null}

          <h2 className="mb-section-label">My trends</h2>
          {data ? (
            <BaselineRibbonChart
              label="Sleep hours against your usual range"
              takeaway="Your sleep has been below your usual rhythm for 3 nights."
              values={data.trends.points}
              variant="detail"
            />
          ) : (
            <p>Your last saved sleep and mood stay on this phone.</p>
          )}

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
          {data && data.ledger.items.length === 0 ? (
            <p>No access yet.</p>
          ) : data ? (
            data.ledger.items.map((item, index) => (
              <AccessLedgerItem
                actor={
                  item.action === "identity.viewed"
                    ? (item.actor_label ?? "Welfare Officer, your unit, viewed your identity")
                    : (item.actor_label ?? item.actor ?? "Officer")
                }
                key={`${item.action ?? "access"}-${index}`}
                purpose={
                  item.action === "identity.viewed"
                    ? "Care contact"
                    : (item.purpose_code ?? "Care")
                }
                when={item.at ?? ""}
              />
            ))
          ) : (
            <p>Saved on this phone. Officers cannot see this list while you are offline.</p>
          )}
          <ReceiptCard hash={receipt.hash} time={receipt.time} />

          <h2 className="mb-section-label">Rights centre</h2>
          {data ? (
            <p>
              Notice {data.rights.notice.version}. Hash {data.rights.notice.hash}.
            </p>
          ) : (
            <p>Rights stay on this phone.</p>
          )}
          <nav aria-label="Rights" className="mb-rights">
            {(data?.rights.actions ?? []).map((action) => (
              <span key={action}>
                {action} <span aria-hidden="true">›</span>
              </span>
            ))}
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
              Erase my data <span aria-hidden="true">›</span>
            </button>
          </nav>

          <h2 className="mb-section-label">Requests</h2>
          <Link href="/app/talk">Counselling bookings and welfare requests</Link>

          <h2 className="mb-section-label">Concerns</h2>
          <Link href="/app/concerns">Raise a grievance and track the SLA</Link>

          <h2 className="mb-section-label">Unit pulse</h2>
          <p>One anonymous question this week. Results are never shown individually.</p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("unit", 1)
                .then(() => setPulseNote("Saved. Command sees a company share, never your name."));
            }}
            type="button"
          >
            This week felt heavy
          </button>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("unit", 0)
                .then(() => setPulseNote("Saved. Command sees a company share, never your name."));
            }}
            type="button"
          >
            This week felt steady
          </button>
          <h2 className="mb-section-label">Trust pulse</h2>
          <p>I believe this system exists to support me.</p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("trust", 1)
                .then(() => setPulseNote("Saved. Trust pulse stays anonymous."));
            }}
            type="button"
          >
            Yes, I believe this system exists to support me
          </button>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("trust", 0)
                .then(() => setPulseNote("Saved. Trust pulse stays anonymous."));
            }}
            type="button"
          >
            Not yet
          </button>
          {pulseNote ? <p>{pulseNote}</p> : null}

          <h2 className="mb-section-label">Things Saathi remembers</h2>
          <p>Off by default. Saved items stay with you, never scoring, never officers.</p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .saveRemembers({ opt_in: !(data?.remembers.opt_in ?? false) })
                .then(() => reload());
            }}
            type="button"
          >
            {(data?.remembers.opt_in ?? false) ? "Turn off remembering" : "Turn on remembering"}
          </button>
          {(data?.remembers.items ?? []).map((item) => (
            <p key={item.text}>
              {item.group}: {item.text}
            </p>
          ))}
          <button
            className="mb-ghost"
            onClick={() => {
              void engineClient().saveRemembers({ forget: true }).then(() => reload());
            }}
            type="button"
          >
            Forget everything
          </button>

          <h2 className="mb-section-label">Settings</h2>
          <label>
            Language
            <select
              onChange={(event) => {
                setLang(event.target.value);
                window.localStorage.setItem("manobal.language", event.target.value);
                void engineClient().savePersonalisation({ language: event.target.value });
              }}
              value={lang}
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="ta">Tamil</option>
            </select>
          </label>
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
            Simple mode, larger buttons
          </label>
          <Link href="/app/plan">My safety plan</Link>
          <Link href="/app/buddy">Buddy</Link>
          <Link href="/app/family">Family connect</Link>
          <Link href="/app/rest">Plan my rest</Link>
          <Link href="/app/assessments">Assessments</Link>
          <Link href="/app/onboarding">Review consent</Link>
        </div>
      ) : null}
    </ScreenState>
  );
}
