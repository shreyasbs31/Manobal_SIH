"use client";

import { DriverList, FormationGrid } from "@manobal/ui";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function CommandPage() {
  const router = useRouter();
  const { data, error, loading, offline } = useEngine("command-posture", (client, signal) =>
    client.commandPosture(signal),
  );
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const [copilot, setCopilot] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [refused, setRefused] = useState(false);
  const [chart, setChart] = useState("40%");
  const [asking, setAsking] = useState(false);
  const [copilotLang, setCopilotLang] = useState("hi");
  const [panel, setPanel] = useState({
    title: "Charlie Coy, W0",
    unit: "Charlie Coy",
    share: "20 to 30%",
    note: "Roster overtime and night load have sat high for three weeks.",
    hidden: false,
  });

  const kpis = useMemo(
    () =>
      data
        ? [
            { label: "Duty hrs", value: data.duty_hours },
            { label: "Rest denials", value: data.rest_denials },
            { label: "Night load", value: data.night_load },
            { label: "Leave backlog", value: data.leave_backlog },
          ]
        : [],
    [data],
  );

  const language = String(profile.data?.copilot_language ?? copilotLang);

  function openRoster(unit: string) {
    window.sessionStorage.setItem("manobal.roster.unit", unit);
    router.push("/command/roster");
  }

  async function ask(nextQuestion: string, lang?: string) {
    const text = nextQuestion.trim();
    if (!text || asking) {
      return;
    }
    setQuestion(text);
    setAsking(true);
    const used = lang ?? (/[ऀ-ॿ]|kaun|pareshan/i.test(text) ? "hi" : "en");
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
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
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
              cells={[...data.cells]}
              onSelect={(cell) => {
                setPanel({
                  title: `${cell.unit}, ${cell.weekLabel}`,
                  unit: cell.unit,
                  share:
                    cell.band === "hidden"
                      ? "Hidden to protect individuals"
                      : (cell.shareLabel ?? "under 10%"),
                  note:
                    cell.band === "hidden"
                      ? "Fewer than 10 people or a recent large change."
                      : cell.unit === "Charlie Coy"
                        ? "Roster overtime and night load have sat high for three weeks."
                        : "Share at T2 or above.",
                  hidden: cell.band === "hidden",
                });
              }}
              sparks={data.sparks}
              takeaway={data.takeaway}
              units={[...data.companies]}
              weeks={12}
            />
            <aside className="mb-sheet">
              <h2>{panel.title}</h2>
              <p className="mb-sheet-metric">Share at T2 or above: {panel.share}</p>
              {panel.hidden ? <p>{panel.note}</p> : <DriverList items={["Roster overtime", "Night load"]} />}
              {copilot ? null : (
                <div className="mb-chip-row">
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      setCopilot(true);
                      void ask(
                        "चार्ली कॉय की ड्यूटी तीन सप्ताह से ऊपर है। क्या रात की पाली घटाई जा सकती है?",
                        "hi",
                      );
                    }}
                    type="button"
                  >
                    रात की पाली
                  </button>
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      setCopilot(true);
                      void ask(
                        "Charlie Coy duty hours have been high for three weeks. Can night share come down?",
                        "en",
                      );
                    }}
                    type="button"
                  >
                    Night share
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
                  Open roster balancer
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => setCopilot((value) => !value)}
                  type="button"
                >
                  {copilot ? "Close copilot" : "Ask copilot"}
                </button>
              </div>
            </aside>
            {copilot ? (
              <aside className="mb-copilot">
                <h2>Copilot</h2>
                <div className="mb-chip-row" role="group" aria-label="Copilot language">
                  {(["hi", "en"] as const).map((code) => (
                    <button
                      aria-pressed={language === code}
                      className="mb-ghost"
                      key={code}
                      onClick={() => {
                        setCopilotLang(code);
                        void engineClient().patchOfficerProfile({ copilot_language: code });
                        profile.reload();
                      }}
                      type="button"
                    >
                      {code === "hi" ? "Hindi" : "English"}
                    </button>
                  ))}
                </div>
                <div className="mb-chip-row">
                  <button
                    className="mb-secondary"
                    onClick={() =>
                      void ask(
                        "चार्ली कॉय की ड्यूटी तीन सप्ताह से ऊपर है। क्या रात की पाली घटाई जा सकती है?",
                        "hi",
                      )
                    }
                    type="button"
                  >
                    रात की पाली
                  </button>
                  <button
                    className="mb-secondary"
                    onClick={() =>
                      void ask(
                        "Charlie Coy duty hours have been high for three weeks. Can night share come down?",
                        "en",
                      )
                    }
                    type="button"
                  >
                    Night share
                  </button>
                  <button
                    className="mb-ghost"
                    onClick={() => void ask("Charlie Coy mein kaun pareshan hai?", "hi")}
                    type="button"
                  >
                    Kaun pareshan hai?
                  </button>
                </div>
                <label>
                  Question
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
                  {asking ? "Asking" : "Ask"}
                </button>
                {answer ? (
                  <>
                    <p lang={refused && /kaun|pareshan|[ऀ-ॿ]/i.test(question) ? "hi" : "en"}>{answer}</p>
                    <p className="mb-hosting-caption">Written by Saathi AI, check before use.</p>
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
