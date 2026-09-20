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

          <nav aria-label="Your choices" className="mb-rights">
            <Link href="/trust">
              Privacy notice <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/talk">
              Talk to a person <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/concerns">
              Raise a concern <span aria-hidden="true">›</span>
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
              Erase my data <span aria-hidden="true">›</span>
            </button>
          </nav>

          <h2 className="mb-section-label">This week</h2>
          <p>Your name is not attached.</p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("unit", 1)
                .then(() => setPulseNote("Saved."));
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
                .then(() => setPulseNote("Saved."));
            }}
            type="button"
          >
            This week felt steady
          </button>
          <p>I believe this app is here to support me.</p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("trust", 1)
                .then(() => setPulseNote("Saved."));
            }}
            type="button"
          >
            Yes
          </button>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .savePulse("trust", 0)
                .then(() => setPulseNote("Saved."));
            }}
            type="button"
          >
            Not yet
          </button>
          {pulseNote ? <p>{pulseNote}</p> : null}

          <h2 className="mb-section-label">What Saathi remembers</h2>
          <p>Off unless you turn it on. Officers never see this.</p>
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
            <p key={item.text}>{item.text}</p>
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
          <label className="mb-field">
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
          <nav aria-label="More on this phone" className="mb-rights">
            <Link href="/app/plan">
              My safety plan <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/buddy">
              Buddy <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/family">
              Family connect <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/rest">
              Plan my rest <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/assessments">
              Assessments <span aria-hidden="true">›</span>
            </Link>
            <Link href="/app/onboarding">
              Review consent <span aria-hidden="true">›</span>
            </Link>
          </nav>
        </div>
      ) : null}
    </ScreenState>
  );
}
