"use client";

import { DriverList, FormationGrid } from "@manobal/ui";
import { useMemo, useState } from "react";

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
  const [provider, setProvider] = useState("");
  const [panel, setPanel] = useState({
    title: "Charlie Coy, W0",
    share: "20 to 30%",
    note: "Top drivers sit at company level. No names, no ranks of people.",
    hidden: false,
  });

  const kpis = useMemo(
    () =>
      data
        ? [
            { label: "Duty hours", value: data.duty_hours, meaning: "Weekly load at company level" },
            { label: "Rest denials", value: data.rest_denials, meaning: "Rest asked and not given" },
            { label: "Night load", value: data.night_load, meaning: "Share of night duty" },
            { label: "Quick returns", value: data.quick_returns ?? "6", meaning: "Short gaps between duties" },
            { label: "Leave backlog", value: data.leave_backlog, meaning: "Days waiting, not people" },
            { label: "Median leave", value: data.median_leave ?? "41 days", meaning: "Days since last leave" },
            { label: "Incident", value: data.incident_exposure ?? "open window", meaning: "Unit window, not names" },
            { label: "Grievance age", value: data.grievance_age ?? "21 days", meaning: "Oldest open category" },
          ]
        : [],
    [data],
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div>
          <p className="mb-desk-intro">
            This desk is for commanders. It shows unit load so you can rest a company, not watch a
            person. Welfare and Medical keep the named cases. You never see a score or a name here.
            Click a company cell, then open the roster balancer to move duty hours and project 14
            days.
          </p>
          <p className="mb-kpi-strip">
            {kpis.map((item) => (
              <span key={item.label}>
                {item.label} <strong>{item.value}</strong>
                <em>{item.meaning}</em>
              </span>
            ))}
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
                      ? "Fewer than 10 people or a recent large change. The tile stays hatched."
                      : cell.unit === "Charlie Coy"
                        ? "Roster overtime and night load have sat high for three weeks."
                        : "Share at T2 or above. Drivers stay at company level.",
                  hidden: cell.band === "hidden",
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
              {panel.hidden ? null : <DriverList items={["Roster overtime", "Night load"]} />}
              <a className="mb-secondary" href="/command/roster">
                Change duty hours and project 14 days
              </a>
              <a className="mb-ghost" href="/command/roster">
                Ease night share on the roster
              </a>
              <button
                className="mb-primary"
                onClick={() => setCopilot((value) => !value)}
                type="button"
              >
                {copilot ? "Close copilot" : "Ask copilot about the unit"}
              </button>
            </aside>
            {copilot ? (
              <aside className="mb-copilot">
                <h2>Copilot</h2>
                <p>
                  Ask about companies, duty, leave, and climate. A question about a person is
                  refused and redirected to an aggregate.
                </p>
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
                <button
                  className="mb-ghost"
                  onClick={() => setQuestion("Charlie Coy mein kaun pareshan hai?")}
                  type="button"
                >
                  Charlie Coy mein kaun pareshan hai?
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
                        setChart(String(result.chart_spec?.value ?? "40%"));
                        setProvider(String(result.provider ?? ""));
                      });
                  }}
                  type="button"
                >
                  Ask
                </button>
                {answer ? (
                  <>
                    <p lang={refused && /kaun|pareshan|[ऀ-ॿ]/i.test(question) ? "hi" : "en"}>{answer}</p>
                    {provider ? <p className="mb-hosting-caption">Answer source {provider}.</p> : null}
                    <p className="mb-hosting-caption">
                      Prototype: open-weight model hosted on Azure. Deployable on force servers.
                    </p>
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
