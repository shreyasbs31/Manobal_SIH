"use client";

import { SimClock } from "@manobal/ui";
import Link from "next/link";
import { useState } from "react";

import { ConsoleChrome } from "@/components/console-chrome";
import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { drainQueue } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";

type Shot = {
  id: string;
  label: string;
  persona: string;
  href: string;
  clicks: string;
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
      setNotice(ok);
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : "Could not complete that action.");
    }
  }

  return (
    <ConsoleChrome>
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-director">
          {data.cost_guard ? (
            <p className="mb-cost-banner" role="status">
              Daily estimated spend is over the cap. Companion stays on the cheaper class.
            </p>
          ) : null}
          <SimClock playing={data.clock.running} value={data.clock.sim_now.replace("T", " ")} />
          {notice ? <p role="status">{notice}</p> : null}
          <div className="mb-action-row">
            <button
              className="mb-secondary"
              onClick={() => void act(() => engineClient().demoClockJump({ running: !data.clock.running }), "Clock toggled.")}
              type="button"
            >
              {data.clock.running ? "Pause" : "Play"}
            </button>
            <button
              className="mb-secondary"
              onClick={() => void act(() => engineClient().demoClockJump({ days: 1 }), "Advanced one day.")}
              type="button"
            >
              +1 day
            </button>
            <button
              className="mb-secondary"
              onClick={() => void act(() => engineClient().demoClockJump({ days: 7 }), "Advanced one week.")}
              type="button"
            >
              +1 week
            </button>
            <button
              className="mb-primary"
              onClick={() => void act(() => engineClient().demoNightly(), "Nightly scoring ran.")}
              type="button"
            >
              Run nightly scoring now
            </button>
            <button
              aria-pressed={air}
              className="mb-secondary"
              onClick={() => {
                const next = !air;
                setAir(next);
                window.localStorage.setItem("manobal.airplane", next ? "1" : "0");
                window.dispatchEvent(new Event("manobal-airplane"));
              }}
              type="button"
            >
              {air ? "Airplane on" : "Airplane off"}
            </button>
            <button
              className="mb-secondary"
              onClick={() =>
                void act(() => engineClient().setEdgeLink(false), "Unit server link down.")
              }
              type="button"
            >
              Hold edge
            </button>
            <button
              className="mb-secondary"
              onClick={() => {
                void drainQueue(async (kind, payload, id) => {
                  await engineClient().syncQueue([
                    { kind, payload: payload as Record<string, unknown>, client_id: id },
                  ]);
                }).then((count) => {
                  setNotice(`Drained ${count}.`);
                  void engineClient().setEdgeLink(true);
                  reload();
                });
              }}
              type="button"
            >
              Drain queue
            </button>
            <button
              className="mb-secondary"
              onClick={() => void act(() => engineClient().demoOutage("open", true), "Open-class outage on.")}
              type="button"
            >
              Simulate outage
            </button>
            <button
              className="mb-secondary"
              onClick={() =>
                void act(
                  () => engineClient().demoResilience(!data.resilience),
                  data.resilience ? "Resilience off." : "Resilience on.",
                )
              }
              type="button"
            >
              Resilience {data.resilience ? "on" : "off"}
            </button>
            <button
              className="mb-secondary"
              onClick={() => void act(() => engineClient().demoWarmup(), "Warm-up finished.")}
              type="button"
            >
              Warm-up
            </button>
            <button
              className="mb-primary"
              onClick={() =>
                void act(async () => {
                  const result = await engineClient().demoReset();
                  setNotice(`Reset in ${result.seconds.toFixed(2)} s.`);
                }, "Reset complete.")
              }
              type="button"
            >
              Reset snapshot
            </button>
          </div>
          <h2>Scenarios</h2>
          <div className="mb-chip-row">
            {data.scenarios.map((row) => (
              <button
                aria-pressed={data.scenario === row.id}
                className="mb-secondary"
                key={row.id}
                onClick={() =>
                  void act(() => engineClient().demoScenario(row.id), `Loaded ${row.label}.`)
                }
                type="button"
              >
                {row.label}
              </button>
            ))}
          </div>
          <h2>Stage presets</h2>
          <table className="mb-compare">
            <caption>One row per recording shot</caption>
            <thead>
              <tr>
                <th scope="col">Shot</th>
                <th scope="col">Open</th>
                <th scope="col">Clicks</th>
              </tr>
            </thead>
            <tbody>
              {data.shots.map((shot) => (
                <tr key={shot.id}>
                  <td>{shot.label}</td>
                  <td>
                    <Link href={shot.href}>{shot.id}</Link>
                  </td>
                  <td>{shot.clicks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </ScreenState>
    </ConsoleChrome>
  );
}
