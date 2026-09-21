"use client";

import { SimClock } from "@manobal/ui";
import Link from "next/link";
import { useState } from "react";

import { ConsoleChrome } from "@/components/console-chrome";
import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { drainQueue } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";
import { announceWorld } from "@/lib/world";

type Shot = {
  id: string;
  label: string;
  persona: string;
  href: string;
  clicks: string;
  expect?: string;
};

type Scenario = { id: string; label: string; href?: string; phone: string; console: string };

type Board = {
  clock: { sim_now: string; running: boolean; speed: number };
  scenario: string;
  scenarios: Scenario[];
  shots: Shot[];
  resilience: boolean;
  cost_guard: boolean;
};

export default function DirectorPage() {
  const { tx } = useConsoleLang();
  const [air, setAir] = useState(
    typeof window === "undefined" ? false : window.localStorage.getItem("manobal.airplane") === "1",
  );
  const [notice, setNotice] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("director", (client, signal) =>
    client.directorBoard(signal) as Promise<Board>,
  );

  async function act(work: () => Promise<unknown>, ok: string) {
    try {
      await work();
      announceWorld("director");
      setNotice(ok);
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : tx.couldNotComplete);
    }
  }

  return (
    <ConsoleChrome>
      <ScreenState
        error={error}
        loading={loading}
        offline={offline}
        empty={!data}
        loadingText={tx.loading}
        offlineText={tx.offlineView}
      >
        {data ? (
          <div className="mb-director mb-desk">
            <p className="mb-desk-purpose">{tx.dirPurpose}</p>
            <p>{tx.dirWhy}</p>
            {data.cost_guard ? (
              <p className="mb-cost-banner" role="status">
                Daily estimated spend is over the cap. Companion stays on the cheaper class.
              </p>
            ) : null}
            {notice ? <p role="status">{notice}</p> : null}
            <section className="mb-sheet">
              <h2>{tx.dirClock}</h2>
              <SimClock playing={data.clock.running} value={data.clock.sim_now.replace("T", " ")} />
              <div className="mb-action-row">
                <button
                  className="mb-secondary"
                  onClick={() =>
                    void act(() => engineClient().demoClockJump({ running: !data.clock.running }), tx.dirClockDone)
                  }
                  type="button"
                >
                  {data.clock.running ? tx.dirPause : tx.dirPlay}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().demoClockJump({ days: 1 }), tx.dirDayDone)}
                  type="button"
                >
                  {tx.dirDay}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().demoClockJump({ days: 7 }), tx.dirWeekDone)}
                  type="button"
                >
                  {tx.dirWeek}
                </button>
                <button
                  className="mb-primary"
                  onClick={() => void act(() => engineClient().demoNightly(), tx.dirNightlyDone)}
                  type="button"
                >
                  {tx.dirNightly}
                </button>
              </div>
            </section>
            <section className="mb-sheet">
              <h2>{tx.dirScenarios}</h2>
              <div className="mb-director-scenarios">
                {data.scenarios.map((row) => (
                  <button
                    aria-pressed={data.scenario === row.id}
                    className="mb-theatre"
                    key={row.id}
                    onClick={() => void act(() => engineClient().demoScenario(row.id), `${tx.dirLoaded} ${row.label}.`)}
                    type="button"
                  >
                    <strong>{row.label}</strong>
                    <span>{row.phone}</span>
                    <em>{row.console}</em>
                  </button>
                ))}
              </div>
            </section>
            <section className="mb-sheet mb-director-wide">
              <h2>{tx.dirShots}</h2>
              <table className="mb-compare">
                <thead>
                  <tr>
                    <th scope="col">{tx.dirShot}</th>
                    <th scope="col">{tx.dirOpen}</th>
                    <th scope="col">{tx.dirDo}</th>
                    <th scope="col">{tx.dirExpect}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.shots.map((shot) => (
                    <tr key={shot.id}>
                      <td>{shot.label}</td>
                      <td>
                        <Link href={shot.href}>{tx.dirOpen}</Link>
                      </td>
                      <td>{shot.clicks}</td>
                      <td>{shot.expect ?? shot.clicks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="mb-sheet mb-director-wide">
              <h2>{tx.dirControls}</h2>
              <div className="mb-action-row">
                <button
                  aria-pressed={air}
                  className="mb-secondary"
                  onClick={() => {
                    const next = !air;
                    setAir(next);
                    window.localStorage.setItem("manobal.airplane", next ? "1" : "0");
                    window.dispatchEvent(new Event("manobal-airplane"));
                    announceWorld("airplane");
                    setNotice(next ? tx.dirAirOn : tx.dirAirOff);
                  }}
                  type="button"
                >
                  {air ? tx.dirAirOn : tx.dirAirOff}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().setEdgeLink(false), tx.dirLinkDown)}
                  type="button"
                >
                  {tx.dirHoldLink}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => {
                    void drainQueue(async (kind, payload, id) => {
                      await engineClient().syncQueue([
                        { kind, payload: payload as Record<string, unknown>, client_id: id },
                      ]);
                    }).then((count) => {
                      setNotice(`${tx.dirDrained} ${count}.`);
                      void engineClient().setEdgeLink(true);
                      reload();
                    });
                  }}
                  type="button"
                >
                  {tx.dirDrain}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().demoOutage("open", true), tx.dirOutageOn)}
                  type="button"
                >
                  {tx.dirOutage}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().demoOutage("deepgram", true), tx.dirSpeechDown)}
                  type="button"
                >
                  {tx.dirSpeechOut}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().demoOutage("deepgram", false), tx.dirSpeechBack)}
                  type="button"
                >
                  {tx.dirSpeechOk}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() =>
                    void act(
                      () => engineClient().demoResilience(!data.resilience),
                      data.resilience ? tx.dirResOff : tx.dirResOn,
                    )
                  }
                  type="button"
                >
                  {tx.dirResilience} {data.resilience ? tx.on : tx.off}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void act(() => engineClient().demoWarmup(), tx.dirWarmDone)}
                  type="button"
                >
                  {tx.dirWarm}
                </button>
                <button
                  className="mb-primary"
                  onClick={() =>
                    void act(async () => {
                      const result = await engineClient().demoReset();
                      setNotice(`${tx.dirResetDone} ${result.seconds.toFixed(2)} s.`);
                    }, tx.dirResetDone)
                  }
                  type="button"
                >
                  {tx.dirReset}
                </button>
              </div>
            </section>
          </div>
        ) : null}
      </ScreenState>
    </ConsoleChrome>
  );
}
