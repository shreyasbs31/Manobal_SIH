"use client";

import { DriverList, FormationGrid } from "@manobal/ui";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { localiseUnit, useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function CommandPage() {
  const router = useRouter();
  const { lang, tx } = useConsoleLang();
  const { data, error, loading, offline } = useEngine("command-posture", (client, signal) =>
    client.commandPosture(signal),
  );
  const [copilot, setCopilot] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [refused, setRefused] = useState(false);
  const [chart, setChart] = useState("40%");
  const [asking, setAsking] = useState(false);
  const [panel, setPanel] = useState({
    title: "",
    unit: "Charlie Coy",
    share: "20 to 30%",
    note: "",
    hidden: false,
  });

  const kpis = useMemo(
    () =>
      data
        ? [
            { label: tx.dutyHrs, value: data.duty_hours },
            { label: tx.restDenials, value: data.rest_denials },
            { label: tx.nightLoad, value: data.night_load },
            { label: tx.leaveBacklog, value: data.leave_backlog },
          ]
        : [],
    [data, tx],
  );

  function openRoster(unit: string) {
    window.sessionStorage.setItem("manobal.roster.unit", unit);
    router.push("/command/roster");
  }

  async function ask(nextQuestion: string) {
    const text = nextQuestion.trim();
    if (!text || asking) {
      return;
    }
    setQuestion(text);
    setAsking(true);
    const used = /[ऀ-ॿ]|kaun|pareshan/i.test(text) ? "hi" : lang;
    try {
      const result = await engineClient().commandCopilot(text, used);
      setAnswer(result.answer);
      setRefused(result.refuse);
      setChart(String(result.chart_spec?.value ?? "40%"));
    } finally {
      setAsking(false);
    }
  }

  return (
    <ScreenState
      error={error}
      loading={loading}
      offline={offline}
      empty={!data}
      loadingText={tx.loading}
      offlineText={tx.offlineView}
    >
      {data ? (
        <div className="mb-desk mb-desk-fill">
          <p className="mb-kpi-strip">
            {kpis.map((item) => (
              <span key={item.label}>
                {item.label} <strong>{item.value}</strong>
              </span>
            ))}
          </p>
          <div className="mb-posture" data-copilot={copilot ? "true" : "false"}>
            <FormationGrid
              cells={(data.cells ?? []).map((cell) => ({
                ...cell,
                unit: localiseUnit(tx, cell.unit),
              }))}
              onSelect={(cell) => {
                const original =
                  (data.companies ?? []).find((name) => localiseUnit(tx, name) === cell.unit) ??
                  cell.unit;
                setPanel({
                  title: `${cell.unit}, ${cell.weekLabel}`,
                  unit: original,
                  share:
                    cell.band === "hidden"
                      ? tx.hiddenPeople
                      : (cell.shareLabel ?? tx.under10),
                  note:
                    cell.band === "hidden"
                      ? tx.hiddenNote
                      : original === "Charlie Coy"
                        ? tx.charlieNote
                        : tx.shareT2Note,
                  hidden: cell.band === "hidden",
                });
              }}
              sparks={Object.fromEntries(
                Object.entries(data.sparks ?? {}).map(([key, value]) => [
                  localiseUnit(tx, key),
                  value,
                ]),
              )}
              takeaway={tx.takeaway}
              copy={{
                unit: tx.unit,
                hidden: tx.hiddenNote,
                usual: tx.usual,
                watch: tx.watch,
                heavy: tx.heavy,
                gridLabel: tx.gridLabel,
              }}
              units={(data.companies ?? []).map((name) => localiseUnit(tx, name))}
              weeks={12}
            />
            <aside className="mb-sheet">
              <h2>{panel.title || `${localiseUnit(tx, "Charlie Coy")}, W0`}</h2>
              <p className="mb-sheet-metric">
                {tx.shareT2}: {panel.share || "20 to 30%"}
              </p>
              {panel.hidden ? (
                <p>{panel.note || tx.hiddenNote}</p>
              ) : (
                <DriverList items={[...tx.drivers]} />
              )}
              {copilot ? null : (
                <div className="mb-chip-row">
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      setCopilot(true);
                      void ask(tx.promptNight);
                    }}
                    type="button"
                  >
                    {tx.promptNightLabel}
                  </button>
                </div>
              )}
              <div className="mb-action-row">
                <button
                  className="mb-primary"
                  disabled={panel.hidden}
                  onClick={() => openRoster(panel.unit)}
                  type="button"
                >
                  {tx.openRoster}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => setCopilot((value) => !value)}
                  type="button"
                >
                  {copilot ? tx.closeCopilot : tx.askCopilot}
                </button>
              </div>
            </aside>
            {copilot ? (
              <aside className="mb-copilot">
                <h2>{tx.copilot}</h2>
                <div className="mb-chip-row">
                  <button
                    className="mb-secondary"
                    onClick={() => void ask(tx.promptNight)}
                    type="button"
                  >
                    {tx.promptNightLabel}
                  </button>
                  <button className="mb-ghost" onClick={() => void ask(tx.promptRefuse)} type="button">
                    {tx.promptRefuseLabel}
                  </button>
                </div>
                <label>
                  {tx.question}
                  <textarea
                    onChange={(event) => setQuestion(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                        event.preventDefault();
                        void ask(question);
                      }
                    }}
                    value={question}
                  />
                </label>
                <button
                  className="mb-primary"
                  disabled={asking || !question.trim()}
                  onClick={() => void ask(question)}
                  type="button"
                >
                  {asking ? tx.asking : tx.ask}
                </button>
                {answer ? (
                  <>
                    <p lang={lang}>{answer}</p>
                    <p className="mb-hosting-caption">{tx.writtenBy}</p>
                  </>
                ) : null}
                {answer && !refused ? (
                  <div className="mb-copilot-chart" aria-hidden="false" data-testid="copilot-chart">
                    <span style={{ width: chart.includes("30") ? "30%" : "50%" }} />
                  </div>
                ) : null}
              </aside>
            ) : null}
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
