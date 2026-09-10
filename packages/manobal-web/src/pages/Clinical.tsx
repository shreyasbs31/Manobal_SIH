import { useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { RulesetProposal, Session } from "../api/types";
import { Notice } from "../components/Notice";
import { ClinicalQueue } from "./ClinicalQueue";

type Props = { session: Session };

export function Clinical({ session }: Props) {
  const api = createClient(session);
  const [proposals, setProposals] = useState<RulesetProposal[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .rulesets()
      .then((body) => setProposals(body.proposals))
      .catch((err: unknown) => {
        setError(
          err instanceof ApiError
            ? err.message
            : "clinical approval is only available to WDEC listing via dual-approval endpoints",
        );
      });
  }, [session.token]);

  return (
    <>
      <h1>Clinical approval</h1>
      <p className="muted">A ruleset is not live until both this desk and WDEC have signed.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {session.role === "medical_officer" ? <ClinicalQueue session={session} /> : null}
      <ul>
        {proposals.map((row) => (
          <li key={row.id}>
            {row.version} [{row.status}]
            <button
              type="button"
              className="ghost"
              onClick={() =>
                void api
                  .approveRuleset(row.id, true)
                  .then(() => api.rulesets())
                  .then((body) => {
                    setError("");
                    setProposals(body.proposals);
                  })
                  .catch((err: unknown) => {
                    setError(err instanceof ApiError ? err.message : "approval refused");
                  })
              }
            >
              Clinical approve
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
