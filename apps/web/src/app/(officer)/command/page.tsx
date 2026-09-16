"use client";

import { DriverList, FormationGrid } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function CommandPage() {
  const { data, error, loading, offline } = useEngine("command-posture", (client, signal) =>
    client.commandPosture(signal),
  );
  const [copilot, setCopilot] = useState(false);

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
              Leave backlog <strong>{data.leave_backlog}</strong>
            </span>
          </p>
          <div className="mb-posture">
            <FormationGrid
              cells={[...data.cells]}
              takeaway={data.takeaway}
              units={[...data.companies]}
              weeks={12}
            />
            <aside>
              <h2>Charlie Coy, W0</h2>
              <p>Share at T2 or above: 20 to 30%</p>
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
          </div>
          {copilot ? (
            <aside className="mb-copilot">
              <h2>Copilot</h2>
              <p>Ask about the unit, never about a person.</p>
              <p lang="hi">चार्ली कॉय की ड्यूटी तीन सप्ताह से ऊपर है। क्या रात की पाली घटाई जा सकती है?</p>
              <p>Charlie Coy duty hours have been high for three weeks. Can night share come down?</p>
            </aside>
          ) : null}
        </div>
      ) : null}
    </ScreenState>
  );
}
