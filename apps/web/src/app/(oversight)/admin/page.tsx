"use client";

import { MachineTranslatedBadge, ValidatedBadge } from "@manobal/ui";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Admin = {
  languages?: { code: string; reviewed: boolean; strings?: number; flag?: string }[];
  flags?: Record<string, boolean>;
  acute_listed?: boolean;
  units?: string[];
  officers?: string[];
  corpus?: { reviewed_en: number; reviewed_hi: number; pending: number; embedded_at?: string };
  tree?: { id: string; label: string; n: number; depth: number }[];
  assignments?: { officer: string; unit: string; valid_until: string }[];
  entra?: { group: string; role: string }[];
  audio?: { files: string[]; reviewed: boolean; live_tts: boolean };
  lexicon?: { version: string; phrases: number; languages: string[] };
};

function asList<T>(value: T[] | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

export default function AdminPage() {
  const { tx } = useConsoleLang();
  const { data, error, loading, offline, reload } = useEngine("admin", (client, signal) =>
    client.adminConsole(signal) as Promise<Admin>,
  );
  const [unit, setUnit] = useState("");
  const [officer, setOfficer] = useState("");
  const [until, setUntil] = useState("2027-03-31");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const tree = asList(data?.tree);
  const flags = data?.flags ?? {};
  const officers = asList(data?.officers);
  const assignments = asList(data?.assignments);
  const entra = asList(data?.entra);
  const languages = asList(data?.languages);
  const selected = useMemo(
    () => tree.find((row) => row.id === unit) ?? tree.find((row) => row.depth === 2),
    [tree, unit],
  );

  function officerLabel(id: string): string {
    return tx.officers[id] ?? id;
  }

  function unitLabel(id: string): string {
    return tree.find((row) => row.id === id)?.label ?? id;
  }

  function flagLabel(name: string): string {
    if (name === "simple_mode_default") return tx.adminSimple;
    if (name === "machine_translate") return tx.adminMt;
    return name;
  }

  async function run(id: string, work: () => Promise<void>) {
    setBusy(id);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : tx.couldNotComplete);
    } finally {
      setBusy(null);
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
        <div className="mb-admin-desk mb-desk">
          <p className="mb-desk-purpose">{tx.adminPurpose}</p>
          {notice ? <p role="status">{notice}</p> : null}
          <div className="mb-admin-layout">
            <section className="mb-sheet mb-admin-scope">
              <div className="mb-section-head">
                <div>
                  <h2>{tx.adminWorkspace}</h2>
                  <p>{tx.adminWorkspaceNote}</p>
                </div>
                <strong>{selected?.label ?? tx.adminPickUnit}</strong>
              </div>
              <div className="mb-admin-scope-grid">
                <div className="mb-admin-tree">
                  <h3>{tx.adminTree}</h3>
                  {tree.map((row) => (
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
                </div>
                <div className="mb-admin-assign">
                  <h3>{tx.adminAssign}</h3>
                  <label>
                    {tx.adminOfficer}
                    <select onChange={(event) => setOfficer(event.target.value)} value={officer}>
                      <option value="">{tx.adminPickOfficer}</option>
                      {officers.map((row) => (
                        <option key={row} value={row}>{officerLabel(row)}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    {tx.unit}
                    <select onChange={(event) => setUnit(event.target.value)} value={unit}>
                      <option value="">{tx.adminPickUnit}</option>
                      {tree.map((row) => (
                        <option key={row.id} value={row.id}>{row.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    {tx.adminUntil}
                    <input onChange={(event) => setUntil(event.target.value)} type="date" value={until} />
                  </label>
                  <button
                    className="mb-primary"
                    disabled={!officer || !unit || busy !== null}
                    onClick={() =>
                      void run("assign", async () => {
                        await engineClient().adminAssign(officer, unit, until);
                        setNotice(
                          `${officerLabel(officer)} ${tx.adminScoped} ${selected?.label ?? unitLabel(unit)} ${tx.adminUntil} ${until}.`,
                        );
                      })
                    }
                    type="button"
                  >
                    {tx.adminSaveAssign}
                  </button>
                </div>
              </div>
              <div className="mb-admin-assignments">
                <h3>{tx.adminAssignmentsActive}</h3>
                {assignments.map((row) => (
                  <article key={row.officer}>
                    <span>{officerLabel(row.officer)}</span>
                    <strong>{unitLabel(row.unit)}</strong>
                    <time>{row.valid_until}</time>
                  </article>
                ))}
              </div>
            </section>
            <section className="mb-sheet mb-admin-safeguards">
              <div className="mb-section-head">
                <div>
                  <h2>{tx.adminSafeguards}</h2>
                  <p>{tx.adminSafeguardsNote}</p>
                </div>
              </div>
              <div className="mb-admin-flags">
                {Object.entries(flags).map(([name, enabled]) => (
                  <div className="mb-switch-cell" key={name}>
                    <span>{flagLabel(name)}</span>
                    <button
                      aria-pressed={enabled}
                      className="mb-toggle"
                      disabled={busy !== null}
                      onClick={() =>
                        void run(name, async () => {
                          await engineClient().adminFlag(name, !enabled);
                          setNotice(`${flagLabel(name)} ${enabled ? tx.off : tx.on}.`);
                        })
                      }
                      type="button"
                    >
                      {enabled ? tx.on : tx.off}
                    </button>
                  </div>
                ))}
                <div className="mb-switch-cell" data-locked="true">
                  <span>{tx.acutePath}</span>
                  <button className="mb-toggle" onClick={() => setNotice(tx.acuteLocked)} type="button">
                    {tx.alwaysOn}
                  </button>
                </div>
              </div>
              <h3>{tx.adminGroups}</h3>
              <div className="mb-admin-groups">
                {entra.map((row) => (
                  <p key={row.group}>
                    <span>{row.group}</span>
                    <strong>{tx.desks[row.role] ?? row.role}</strong>
                  </p>
                ))}
              </div>
            </section>
            <section className="mb-sheet mb-admin-content">
              <div className="mb-section-head">
                <div>
                  <h2>{tx.adminContent}</h2>
                  <p>{tx.adminContentNote}</p>
                </div>
              </div>
              <div className="mb-admin-content-grid">
                <article>
                  <h3>{tx.adminLang}</h3>
                  <div className="mb-chip-row">
                    {languages.map((row) => (
                      <span className="mb-lang-chip" key={row.code}>
                        {row.code}
                        {row.strings ? ` ${row.strings}` : ""}
                        {row.reviewed ? <ValidatedBadge /> : <MachineTranslatedBadge />}
                      </span>
                    ))}
                  </div>
                  <p>
                    {data.lexicon?.phrases ?? 0} {tx.adminPhrasesIn} {data.lexicon?.languages.length ?? 0} {tx.adminLangCount}.
                  </p>
                </article>
                <article>
                  <h3>{tx.adminKnowledge}</h3>
                  <p>
                    {tx.adminEnglish} {data.corpus?.reviewed_en ?? 0}, {tx.adminHindi} {data.corpus?.reviewed_hi ?? 0}
                    {data.corpus?.pending ? `, ${data.corpus.pending} ${tx.adminWaiting}` : ""}.
                  </p>
                  {data.corpus?.embedded_at ? <p>{tx.adminLastUpdated} {data.corpus.embedded_at}.</p> : null}
                  <button
                    className="mb-secondary"
                    disabled={busy !== null}
                    onClick={() =>
                      void run("embed", async () => {
                        await engineClient().adminReembed();
                        setNotice(tx.adminRefresh);
                      })
                    }
                    type="button"
                  >
                    {tx.adminRefresh}
                  </button>
                </article>
                <article>
                  <h3>{tx.adminAudio}</h3>
                  <strong>{data.audio?.files.length ?? 0} {tx.adminAudioFiles}</strong>
                  <p>{data.audio?.reviewed ? tx.adminReviewed : tx.adminNeedsReview}</p>
                </article>
              </div>
            </section>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
