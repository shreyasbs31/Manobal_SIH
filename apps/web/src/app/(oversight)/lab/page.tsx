"use client";

import { KpiTile, LeadTimeChart, ReliabilityChart } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Lab = {
  world: string;
  source?: string;
  metrics: Record<string, number>;
  calibration: { predicted: number; observed: number }[];
  confusion: { tp: number; fp: number; tn: number; fn: number };
  ablations: { name: string; delta: string; note: string }[];
  zero_penalty?: { excluded: string[]; present_in_model: boolean; note: string };
  personas: { imran: string; thomas: string };
  honest: string;
  lead_days?: number[];
  lead_median?: number | null;
  metrics_primary?: Record<string, number>;
  metrics_shifted?: Record<string, number>;
  sample_size?: number;
  world_note?: string;
};

function metricValue(metrics: Record<string, number>, key: string): string {
  const value = metrics[key];
  return typeof value === "number" ? value.toFixed(2) : "n/a";
}

function metricPercent(metrics: Record<string, number>, key: string): string {
  const value = metrics[key];
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "n/a";
}

export default function LabPage() {
  const { lang, tx } = useConsoleLang();
  const [world, setWorld] = useState("primary");
  const [bench, setBench] = useState<string | null>(null);
  const { data, error, loading, offline } = useEngine(`lab-${world}`, (client, signal) =>
    client.labMetrics(world, signal) as Promise<Lab>,
  );
  const metrics = data?.metrics ?? {};
  const leadDays = Array.isArray(data?.lead_days) ? data.lead_days : [];
  const sortedLead = [...leadDays].sort((a, b) => a - b);
  const fallbackMedian =
    sortedLead.length === 0
      ? null
      : sortedLead.length % 2
        ? (sortedLead[Math.floor(sortedLead.length / 2)] ?? null)
        : ((sortedLead[sortedLead.length / 2 - 1] ?? 0) + (sortedLead[sortedLead.length / 2] ?? 0)) / 2;
  const leadMedian = data?.lead_median ?? fallbackMedian;
  const withinFour =
    leadDays.length > 0
      ? Math.round((leadDays.filter((value) => value <= 4).length / leadDays.length) * 100)
      : 0;

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
        <div className="mb-lab-desk mb-desk">
          <p className="mb-desk-purpose">{tx.labPurpose}</p>
          <section className="mb-sheet mb-lab-question">
            <div>
              <h2>{tx.labQuestion}</h2>
              <p>{tx.labQuestionBody}</p>
              <p className="mb-lab-honest">{tx.labNotField}</p>
            </div>
            <div className="mb-lab-controls">
              <span>{tx.labWorld}</span>
              <div className="mb-segmented">
                <button
                  aria-pressed={world === "primary"}
                  onClick={() => setWorld("primary")}
                  type="button"
                >
                  {tx.labPrimary}
                </button>
                <button
                  aria-pressed={world === "shifted"}
                  onClick={() => setWorld("shifted")}
                  type="button"
                >
                  {tx.labShifted}
                </button>
              </div>
              <button
                className="mb-primary"
                onClick={() => {
                  void engineClient()
                    .labBenchmark()
                    .then((result) => {
                      setBench(`${result.subjects} ${tx.labCount.toLowerCase()} in ${result.seconds.toFixed(3)} s`);
                    });
                }}
                type="button"
              >
                {tx.labRun}
              </button>
            </div>
          </section>
          {bench ? <p className="mb-lab-benchmark" role="status">{bench}</p> : null}
          <section className="mb-lab-performance">
            <div className="mb-section-head">
              <div>
                <h2>{tx.labPerformance}</h2>
                <p>{world === "primary" ? tx.labPrimaryReadout : tx.labShiftedReadout}</p>
              </div>
              <strong>{data.sample_size ?? leadDays.length} {tx.labSample}</strong>
            </div>
            <div className="mb-lab-metrics">
              <KpiTile hint={tx.labRecall} label={tx.labCatches} value={metricPercent(metrics, "recall")} />
              <KpiTile hint={tx.labPrecision} label={tx.labAvoids} value={metricPercent(metrics, "precision")} />
              <KpiTile hint={tx.labBrier} label={tx.labCalibrationError} value={metricValue(metrics, "brier")} />
              <KpiTile hint={tx.labF1} label={tx.labF1} value={metricValue(metrics, "f1")} />
            </div>
          </section>
          <section className="mb-sheet mb-lab-lead">
            <div className="mb-section-head">
              <div>
                <h2>{tx.labLead}</h2>
                <p>{tx.labLeadHint}</p>
              </div>
              <strong>{world === "primary" ? tx.labPrimary : tx.labShifted}</strong>
            </div>
            <div className="mb-lab-lead-layout">
              <LeadTimeChart
                countLabel={tx.labCount}
                daysLabel={tx.labDays}
                medianLabel={tx.labMedian}
                values={leadDays}
              />
              <aside className="mb-lab-readout">
                <span>
                  <strong>{leadMedian === null ? "n/a" : leadMedian.toFixed(1)}</strong>
                  {tx.labMedianDays}
                </span>
                <span>
                  <strong>{withinFour}%</strong>
                  {tx.labWithinFour}
                </span>
                <span>
                  <strong>{data.sample_size ?? leadDays.length}</strong>
                  {tx.labSample}
                </span>
                <p>{data.world_note ?? (world === "primary" ? tx.labPrimaryReadout : tx.labShiftedReadout)}</p>
              </aside>
            </div>
          </section>
          <div className="mb-lab-details">
            <section className="mb-sheet">
              <h2>{tx.labConfusion}</h2>
              <div className="mb-conf-matrix" role="table" aria-label={tx.labConfusion}>
                <span />
                <span>{tx.labObservedHigh}</span>
                <span>{tx.labObservedSteady}</span>
                <span>{tx.labModelHigh}</span>
                <strong>{data.confusion.tp}</strong>
                <strong>{data.confusion.fp}</strong>
                <span>{tx.labModelSteady}</span>
                <strong>{data.confusion.fn}</strong>
                <strong>{data.confusion.tn}</strong>
              </div>
            </section>
            <section className="mb-sheet">
              <h2>{tx.labReliability}</h2>
              <p>{tx.labRelHint}</p>
              <ReliabilityChart
                observedLabel={tx.labObserved}
                points={data.calibration}
                predictedLabel={tx.labPredicted}
              />
            </section>
            <section className="mb-sheet mb-lab-ablation">
              <h2>{tx.labAblations}</h2>
              <p>{tx.labAblationNote}</p>
              {data.ablations.map((row) => (
                <article className="mb-ablation-row" key={row.name}>
                  <strong>{row.name}</strong>
                  <span>{row.delta}</span>
                  <p>{row.note}</p>
                </article>
              ))}
              <h3>{tx.labHeldOutTitle}</h3>
              <p>{lang === "hi" ? tx.labImranCheck : data.personas.imran}</p>
              <p>{lang === "hi" ? tx.labThomasCheck : data.personas.thomas}</p>
              {data.zero_penalty ? (
                <details>
                  <summary>{tx.labZero}</summary>
                  <p>{data.zero_penalty.note}</p>
                  <p>{data.zero_penalty.excluded.join(", ")}</p>
                </details>
              ) : null}
            </section>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
