"use client";

import { MachineTranslatedBadge, ValidatedBadge } from "@manobal/ui";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Admin = {
  languages: { code: string; reviewed: boolean; strings?: number; flag?: string }[];
  flags: Record<string, boolean>;
  acute_listed: boolean;
  units: string[];
  officers: string[];
  corpus: { reviewed_en: number; reviewed_hi: number; pending: number };
};

export default function AdminPage() {
  const { data, error, loading, offline, reload } = useEngine("admin", (client, signal) =>
    client.adminConsole(signal) as Promise<Admin>,
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-admin">
          <p>
            Language catalog, reviewed corpus, units, and officer assignments. The acute path is not
            a flag.
          </p>
          <h2>Languages</h2>
          <table className="mb-compare">
            <caption>Reviewed catalog</caption>
            <thead>
              <tr>
                <th scope="col">Language</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.languages.map((row) => (
                <tr key={row.code}>
                  <td>{row.code}</td>
                  <td>{row.reviewed ? <ValidatedBadge /> : <MachineTranslatedBadge />}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>Flags</h2>
          {Object.entries(data.flags).map(([name, enabled]) => (
            <div className="mb-kill" key={name}>
              <span>{name}</span>
              <button
                className="mb-toggle"
                onClick={() => {
                  void engineClient()
                    .adminFlag(name, !enabled)
                    .then(() => reload());
                }}
                type="button"
              >
                {enabled ? "On" : "Off"}
              </button>
            </div>
          ))}
          <p>{data.acute_listed ? "Acute is listed. That is a defect." : "Acute is not listed."}</p>
          <h2>Units</h2>
          <p>{data.units.join(", ")}</p>
          <h2>Corpus</h2>
          <p>
            English {data.corpus.reviewed_en}. Hindi {data.corpus.reviewed_hi}. Pending{" "}
            {data.corpus.pending}.
          </p>
        </div>
      ) : null}
    </ScreenState>
  );
}
