import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { Anchor, BreakGlassGrant, RulesetProposal, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { formatWhen } from "../ui/format";
import { WdecOversight } from "./WdecOversight";

type Props = { session: Session };

export function Wdec({ session }: Props) {
  const api = createClient(session);
  const [grants, setGrants] = useState<BreakGlassGrant[]>([]);
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [proposals, setProposals] = useState<RulesetProposal[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const [glass, chain, rules] = await Promise.all([
      api.breakGlass(),
      api.anchors(),
      api.rulesets(),
    ]);
    setGrants(glass.grants);
    setAnchors(chain.anchors);
    setProposals(rules.proposals);
    setLoaded(true);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setLoaded(true);
      setError(err instanceof ApiError ? err.message : "oversight surfaces unavailable");
    });
  }, [session.token]);

  async function propose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.proposeRuleset({
        version: String(form.get("version")),
        digest: String(form.get("digest")),
        signature: String(form.get("signature")),
        signing_key_id: String(form.get("signing_key_id")),
      });
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not propose this ruleset");
    }
  }

  async function approve(id: number) {
    try {
      await api.approveRuleset(id, false);
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "approval refused");
    }
  }

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Oversight"
        title="Welfare Data Ethics Cell"
        lede="Oversight of accesses and rules. Not a window onto individual records."
      />
      {error ? <Notice tone="error">{error}</Notice> : null}

      <WdecOversight session={session} />

      <section className="panel">
        <h2>Unreviewed break-glass</h2>
        {loaded && !grants.length ? (
          <EmptyState title="No unreviewed grants">Break-glass events that still need review will list here.</EmptyState>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Grant</th>
                <th>Officer</th>
                <th>Justification</th>
              </tr>
            </thead>
            <tbody>
              {grants.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.grantee_id}</td>
                  <td>{row.justification}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <h2>Audit anchors</h2>
        {loaded && !anchors.length ? (
          <EmptyState title="No anchors published">Nightly chain heads appear here once they are sealed.</EmptyState>
        ) : (
          <ul>
            {anchors.map((row) => (
              <li key={row.head_hash}>
                {formatWhen(row.anchored_at)} · {row.event_count} events · {row.head_hash.slice(0, 16)}…
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2>Ruleset proposals</h2>
        {loaded && !proposals.length ? (
          <EmptyState title="No proposals">Propose a signed digest. It stays inactive until both desks sign.</EmptyState>
        ) : (
          <ul>
            {proposals.map((row) => (
              <li key={row.id}>
                {row.version} [{row.status}]
                <button type="button" className="ghost" onClick={() => void approve(row.id)}>
                  WDEC approve
                </button>
              </li>
            ))}
          </ul>
        )}
        <form className="grid two" onSubmit={(event) => void propose(event)}>
          <label htmlFor="version">
            Version
            <input id="version" name="version" required aria-required="true" />
          </label>
          <label htmlFor="digest">
            Digest
            <input id="digest" name="digest" required aria-required="true" />
          </label>
          <label htmlFor="signature">
            Signature
            <input id="signature" name="signature" required aria-required="true" />
          </label>
          <label htmlFor="signing_key_id">
            Signing key
            <input id="signing_key_id" name="signing_key_id" required aria-required="true" />
          </label>
          <div>
            <button type="submit">Propose</button>
          </div>
        </form>
      </section>
    </div>
  );
}
