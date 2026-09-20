"use client";

import { MachineTranslatedBadge, ValidatedBadge } from "@manobal/ui";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Admin = {
  languages: { code: string; reviewed: boolean; strings?: number; flag?: string }[];
  flags: Record<string, boolean>;
  acute_listed: boolean;
  units: string[];
  officers: string[];
  corpus: { reviewed_en: number; reviewed_hi: number; pending: number; embedded_at?: string };
  tree: { id: string; label: string; n: number; depth: number }[];
  assignments: { officer: string; unit: string; valid_until: string }[];
  entra: { group: string; role: string }[];
  audio: { files: string[]; reviewed: boolean; live_tts: boolean };
  lexicon: { version: string; phrases: number; languages: string[] };
};

const FLAG_LABELS: Record<string, string> = {
  simple_mode_default: "Simple mode by default",
  machine_translate: "Machine translation",
};

export default function AdminPage() {
  const { data, error, loading, offline, reload } = useEngine("admin", (client, signal) =>
    client.adminConsole(signal) as Promise<Admin>,
  );
  const [unit, setUnit] = useState("");
  const [officer, setOfficer] = useState("");
  const [until, setUntil] = useState("2027-03-31");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const selected = useMemo(
    () => data?.tree.find((row) => row.id === unit) ?? data?.tree.find((row) => row.depth === 2),
    [data, unit],
  );

  async function run(id: string, work: () => Promise<void>) {
    setBusy(id);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : "Could not complete that action.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-admin mb-desk">
          {notice ? <p role="status">{notice}</p> : null}
          <section className="mb-sheet">
            <h2>Org tree</h2>
            {data.tree.map((row) => (
              <button
                aria-pressed={selected?.id === row.id}
                className="mb-tree-node"
                key={row.id}
                onClick={() => setUnit(row.id)}
                style={{ paddingInlineStart: `${10 + row.depth * 14}px` }}
                type="button"
              >
                <span>{row.label}</span>
                <strong>{row.n}</strong>
              </button>
            ))}
          </section>
          <section className="mb-sheet">
            <h2>Flags</h2>
            {Object.entries(data.flags).map(([name, enabled]) => (
              <div className="mb-kill" key={name}>
                <span>{FLAG_LABELS[name] ?? name}</span>
                <button
                  aria-pressed={enabled}
                  className="mb-toggle"
                  disabled={busy !== null}
                  onClick={() =>
                    void run(name, async () => {
                      await engineClient().adminFlag(name, !enabled);
                      setNotice(`${FLAG_LABELS[name] ?? name} ${enabled ? "off" : "on"}.`);
                    })
                  }
                  type="button"
                >
                  {enabled ? "On" : "Off"}
                </button>
              </div>
            ))}
            <div className="mb-kill" data-locked="true">
              <span>Acute path</span>
              <button className="mb-toggle" disabled type="button">
                Always on
              </button>
            </div>
          </section>
          <section className="mb-sheet">
            <h2>Assign</h2>
            <div className="mb-action-row">
              <label>
                Officer
                <select onChange={(event) => setOfficer(event.target.value)} value={officer}>
                  <option value="">Pick officer</option>
                  {data.officers.map((row) => (
                    <option key={row} value={row}>
                      {row}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Unit
                <select onChange={(event) => setUnit(event.target.value)} value={unit}>
                  <option value="">Pick unit</option>
                  {data.tree.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Valid until
                <input onChange={(event) => setUntil(event.target.value)} type="date" value={until} />
              </label>
              <button
                className="mb-primary"
                disabled={!officer || !unit || busy !== null}
                onClick={() =>
                  void run("assign", async () => {
                    await engineClient().adminAssign(officer, unit, until);
                    setNotice(`${officer} scoped to ${selected?.label ?? unit} until ${until}.`);
                  })
                }
                type="button"
              >
                Save assignment
              </button>
            </div>
            {data.assignments.map((row) => (
              <article className="mb-job-row" key={row.officer}>
                <span>{row.officer}</span>
                <strong>{row.unit}</strong>
                <em>Until {row.valid_until}</em>
                <span />
                <span />
              </article>
            ))}
          </section>
          <section className="mb-sheet">
            <h2>Sign-in groups</h2>
            <table className="mb-compare">
              <thead>
                <tr>
                  <th scope="col">Group</th>
                  <th scope="col">Desk</th>
                </tr>
              </thead>
              <tbody>
                {data.entra.map((row) => (
                  <tr key={row.group}>
                    <td>{row.group}</td>
                    <td>{row.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="mb-sheet">
            <h2>Languages</h2>
            <div className="mb-chip-row">
              {data.languages.map((row) => (
                <span className="mb-lang-chip" key={row.code}>
                  {row.code}
                  {row.strings ? ` ${row.strings}` : ""}
                  {row.reviewed ? <ValidatedBadge /> : <MachineTranslatedBadge />}
                </span>
              ))}
            </div>
            <p>
              {data.lexicon.phrases} crisis phrases in {data.lexicon.languages.length} languages.
            </p>
          </section>
          <section className="mb-sheet">
            <h2>Knowledge</h2>
            <p>
              English {data.corpus.reviewed_en} reviewed, Hindi {data.corpus.reviewed_hi} reviewed
              {data.corpus.pending ? `, ${data.corpus.pending} waiting` : ""}.
            </p>
            {data.corpus.embedded_at ? <p>Last updated {data.corpus.embedded_at}.</p> : null}
            <button
              className="mb-secondary"
              disabled={busy !== null}
              onClick={() =>
                void run("embed", async () => {
                  await engineClient().adminReembed();
                  setNotice("Knowledge refreshed.");
                })
              }
              type="button"
            >
              Refresh knowledge
            </button>
          </section>
          <section className="mb-sheet mb-admin-wide">
            <h2>Audio clips</h2>
            <p>{data.audio.reviewed ? "Reviewed and ready." : "Needs review."}</p>
          </section>
        </div>
      ) : null}
    </ScreenState>
  );
}
