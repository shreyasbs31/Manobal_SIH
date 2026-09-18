"use client";

import { KpiTile, ReliabilityChart } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Lab = {
  world: string;
  source?: string;
  metrics: Record<string, number>;
  calibration: { predicted: number; observed: number }[];
  confusion: { tp: number; fp: number; tn: number; fn: number };
  ablations: { name: string; delta: string; note: string }[];
  zero_penalty: { excluded: string[]; present_in_model: boolean; note: string };
  personas: { imran: string; thomas: string };
  honest: string;
};

export default function LabPage() {
  const [world, setWorld] = useState("primary");
  const [bench, setBench] = useState<string | null>(null);
  const { data, error, loading, offline } = useEngine(`lab-${world}`, (client, signal) =>
    client.labMetrics(world, signal) as Promise<Lab>,
  );

  const metrics = data?.metrics ?? {};

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-lab">
          <p>
            Primary and shifted synthetic worlds sit side by side. Numbers belong here, not on
            command screens.
          </p>
          <p>Source: {data.source ?? "core or demo cases"}.</p>
          <div className="mb-action-row">
            <button
              aria-pressed={world === "primary"}
              className="mb-secondary"
              onClick={() => setWorld("primary")}
              type="button"
            >
              Primary world
            </button>
            <button
              aria-pressed={world === "shifted"}
              className="mb-secondary"
              onClick={() => setWorld("shifted")}
              type="button"
            >
              Shifted world
            </button>
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .labBenchmark()
                  .then((result) => {
                    setBench(`${result.subjects} subjects in ${result.seconds.toFixed(3)} s`);
                  });
              }}
              type="button"
            >
              Run 80,000 in-memory benchmark
            </button>
          </div>
          {bench ? <p role="status">{bench}</p> : null}
          <div className="mb-kpi-row">
            <KpiTile
              hint="T2+"
              label="Precision"
              value={typeof metrics.precision === "number" ? metrics.precision.toFixed(2) : "n/a"}
            />
            <KpiTile
              hint="T2+"
              label="Recall"
              value={typeof metrics.recall === "number" ? metrics.recall.toFixed(2) : "n/a"}
            />
            <KpiTile
              hint="Brier"
              label="Brier"
              value={typeof metrics.brier === "number" ? metrics.brier.toFixed(2) : "n/a"}
            />
          </div>
          <section className="mb-card">
            <h2>Reliability, {data.world} world</h2>
            <ReliabilityChart points={data.calibration} />
          </section>
          <section className="mb-card">
            <h2>Confusion</h2>
            <p>
              True high {data.confusion.tp}. False high {data.confusion.fp}. True steady{" "}
              {data.confusion.tn}. Missed {data.confusion.fn}.
            </p>
          </section>
          <section className="mb-card">
            <h2>Ablations</h2>
            <ul>
              {data.ablations.map((row) => (
                <li key={row.name}>
                  {row.name}: {row.delta}. {row.note}
                </li>
              ))}
            </ul>
          </section>
          <section className="mb-card">
            <h2>Zero penalty</h2>
            <p>{data.zero_penalty.note}</p>
            <p>Present in the model: {data.zero_penalty.present_in_model ? "yes" : "no"}.</p>
          </section>
          <section className="mb-card">
            <h2>Two people who stayed steady</h2>
            <p>{data.personas.imran}</p>
            <p>{data.personas.thomas}</p>
          </section>
          <p>{data.honest}</p>
        </div>
      ) : null}
    </ScreenState>
  );
}
