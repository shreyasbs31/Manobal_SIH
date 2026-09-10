import { useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { RulesetProposal, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { ClinicalQueue } from "./ClinicalQueue";

type Props = { session: Session };

export function Clinical({ session }: Props) {
  const api = createClient(session);
  const [proposals, setProposals] = useState<RulesetProposal[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    void api
      .rulesets()
      .then((body) => {
        setProposals(body.proposals);
        setLoaded(true);
      })
      .catch((err: unknown) => {
        setLoaded(true);
        setError(
          err instanceof ApiError
            ? err.message
            : "clinical approval is only available to WDEC listing via dual-approval endpoints",
        );
      });
  }, [session.token]);

  async function approve(id: number) {
    try {
      await api.approveRuleset(id, true);
      const body = await api.rulesets();
      setError("");
      setProposals(body.proposals);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "approval refused");
    }
  }

  return (
    <div className="stack">
      <PageHeader
        eyebrow={session.role === "medical_officer" ? "Medical officer" : "Clinical dual-approval"}
        title="Clinical approval"
        lede="A ruleset is not live until both this desk and WDEC have signed."
      />
      {error ? <Notice tone="error">{error}</Notice> : null}
      {session.role === "medical_officer" ? <ClinicalQueue session={session} /> : null}
      {loaded && !proposals.length ? (
        <EmptyState title="No rulesets waiting">Proposals from WDEC appear here for the second signature.</EmptyState>
      ) : (
        <ul>
          {proposals.map((row) => (
            <li key={row.id}>
              {row.version} [{row.status}]
              <button type="button" className="ghost" onClick={() => void approve(row.id)}>
                Clinical approve
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
