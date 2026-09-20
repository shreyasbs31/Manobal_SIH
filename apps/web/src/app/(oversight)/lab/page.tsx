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
  const [picked, setPicked] = useState("");
  const { data, error, loading, offline } = useEngine(`lab-${world}`, (client, signal) =>
    client.labMetrics(world, signal) as Promise<Lab>,
  );

  const metrics = data?.metrics ?? {};

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-lab mb-desk">
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
              className="mb-primary"
              onClick={() => {
                void engineClient()
                  .labBenchmark()
                  .then((result) => {
                    setBench(`${result.subjects} subjects in ${result.seconds.toFixed(3)} s`);
                  });
              }}
              type="button"
            >
              Run the large check
            </button>
          </div>
          {bench ? <p role="status">{bench}</p> : null}
          <div className="mb-kpi-row mb-kpi-row-wide">
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
          <section className="mb-sheet">
            <h2>Reliability, {data.world} world</h2>
            <ReliabilityChart points={data.calibration} />
          </section>
          <section className="mb-sheet">
            <h2>Confusion</h2>
            <div className="mb-conf-grid">
              <span>True high {data.confusion.tp}</span>
              <span>False high {data.confusion.fp}</span>
              <span>True steady {data.confusion.tn}</span>
              <span>Missed {data.confusion.fn}</span>
            </div>
          </section>
          <section className="mb-sheet">
            <h2>Ablations</h2>
            {data.ablations.map((row) => (
              <button
                aria-pressed={picked === row.name}
                className="mb-compare-band"
                key={row.name}
                onClick={() => setPicked(row.name)}
                type="button"
              >
                <span>{row.name}</span>
                <strong>{row.delta}</strong>
                {picked === row.name ? <em>{row.note}</em> : null}
              </button>
            ))}
            <button
              aria-pressed={picked === "imran"}
              className="mb-compare-band"
              onClick={() => setPicked("imran")}
              type="button"
            >
              <span>Imran</span>
              <strong>held out</strong>
              {picked === "imran" ? <em>{data.personas.imran}</em> : null}
            </button>
            <button
              aria-pressed={picked === "thomas"}
              className="mb-compare-band"
              onClick={() => setPicked("thomas")}
              type="button"
            >
              <span>Thomas</span>
              <strong>held out</strong>
              {picked === "thomas" ? <em>{data.personas.thomas}</em> : null}
            </button>
          </section>
        </div>
      ) : null}
    </ScreenState>
  );
}
