"use client";

import { DriverList, FormationGrid } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function CommandPage() {
  const { data, error, loading, offline } = useEngine("command-posture", (client, signal) =>
    client.commandPosture(signal),
  );
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const [copilot, setCopilot] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [refused, setRefused] = useState(false);
  const [chart, setChart] = useState("40%");
  const [panel, setPanel] = useState({
    title: "Charlie Coy, W0",
    share: "20 to 30%",
    note: "Top drivers sit at company level.",
  });

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div>
          <p className="mb-kpi-strip">
            <span>
              Duty hrs <strong>{data.duty_hours}</strong>
            </span>
            <span>
              Rest denials <strong>{data.rest_denials}</strong>
            </span>
            <span>
              Night load <strong>{data.night_load}</strong>
            </span>
            <span>
              Quick returns <strong>{data.quick_returns ?? "6"}</strong>
            </span>
            <span>
              Leave backlog <strong>{data.leave_backlog}</strong>
            </span>
            <span>
              Median leave <strong>{data.median_leave ?? "41 days"}</strong>
            </span>
            <span>
              Incident <strong>{data.incident_exposure ?? "open window"}</strong>
            </span>
            <span>
              Grievance age <strong>{data.grievance_age ?? "21 days"}</strong>
            </span>
          </p>
          <div className="mb-posture" data-copilot={copilot ? "true" : "false"}>
            <FormationGrid
              cells={[...data.cells]}
              onSelect={(cell) => {
                setPanel({
                  title: `${cell.unit}, ${cell.weekLabel}`,
                  share:
                    cell.band === "hidden"
                      ? "Hidden to protect individuals"
                      : (cell.shareLabel ?? "under 10%"),
                  note:
                    cell.band === "hidden"
                      ? "Fewer than 10 people or recent large changes."
                      : "Top drivers: roster overtime, night load.",
                });
              }}
              sparks={data.sparks}
              takeaway={data.takeaway}
              units={[...data.companies]}
              weeks={12}
            />
            <aside>
              <h2>{panel.title}</h2>
              <p>Share at T2 or above: {panel.share}</p>
              <p>{panel.note}</p>
              <DriverList items={["Roster overtime", "Night load"]} />
              <a className="mb-secondary" href="/command/roster">
                Open roster balancer
              </a>
              <button
                className="mb-primary"
                onClick={() => setCopilot((value) => !value)}
                type="button"
              >
                {copilot ? "Close copilot" : "Open copilot"}
              </button>
            </aside>
            {copilot ? (
              <aside className="mb-copilot">
                <h2>Copilot</h2>
                <p>Ask about the unit, never about a person.</p>
                {profile.data ? (
                  <p>Copilot language {String(profile.data.copilot_language ?? "hi")}.</p>
                ) : null}
                <button
                  className="mb-ghost"
                  onClick={() =>
                    setQuestion("चार्ली कॉय की ड्यूटी तीन सप्ताह से ऊपर है। क्या रात की पाली घटाई जा सकती है?")
                  }
                  type="button"
                >
                  चार्ली कॉय की ड्यूटी तीन सप्ताह से ऊपर है। क्या रात की पाली घटाई जा सकती है?
                </button>
                <button
                  className="mb-ghost"
                  onClick={() =>
                    setQuestion(
                      "Charlie Coy duty hours have been high for three weeks. Can night share come down?",
                    )
                  }
                  type="button"
                >
                  Charlie Coy duty hours have been high for three weeks. Can night share come down?
                </button>
                <label>
                  Question
                  <textarea onChange={(event) => setQuestion(event.target.value)} value={question} />
                </label>
                <button
                  className="mb-primary"
                  onClick={() => {
                    const lang = /[ऀ-ॿ]|kaun|pareshan/i.test(question) ? "hi" : "en";
                    void engineClient()
                      .commandCopilot(question, lang)
                      .then((result) => {
                        setAnswer(result.answer);
                        setRefused(result.refuse);
                        setChart(result.chart_spec.value);
                      });
                  }}
                  type="button"
                >
                  Ask
                </button>
                {answer ? (
                  <p lang={refused && /kaun|pareshan|[ऀ-ॿ]/i.test(question) ? "hi" : "en"}>{answer}</p>
                ) : null}
                <div className="mb-copilot-chart" aria-hidden="true">
                  <span style={{ width: chart.includes("30") ? "30%" : "50%" }} />
                </div>
              </aside>
            ) : null}
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
