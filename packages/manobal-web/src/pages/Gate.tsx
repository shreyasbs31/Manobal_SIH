import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { mintDevToken } from "../api/client";
import type { Role } from "../api/types";
import { homeFor, writeSession } from "../auth/session";
import { Notice } from "../components/Notice";

const ROLES: { role: Role; actor: string; unit: string; label: string; desk: string }[] = [
  {
    role: "personnel",
    actor: "tok_seed_0000",
    unit: "12BN_A",
    label: "Personnel",
    desk: "Today’s picture, next actions, and a check-in that can change it",
  },
  {
    role: "welfare_officer",
    actor: "officer-001",
    unit: "12BN",
    label: "Welfare officer",
    desk: "Assigned flags. Category names only — never a score",
  },
  {
    role: "medical_officer",
    actor: "medical-001",
    unit: "12BN",
    label: "Medical officer",
    desk: "Clinical referrals. You are never the case assignee",
  },
  {
    role: "commander",
    actor: "commander-001",
    unit: "12BN_A",
    label: "Commander",
    desk: "Unit picture. Individuals never appear",
  },
  {
    role: "wdec_auditor",
    actor: "wdec-001",
    unit: "CENTRAL",
    label: "WDEC auditor",
    desk: "Fairness, audit trail and dual-approval of rules",
  },
];

type Props = {
  subjectToken: string;
  llmConfigured?: boolean;
  onReady: () => void;
};

export function Gate({ subjectToken, llmConfigured = false, onReady }: Props) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function enter(role: Role, actor: string, unit: string) {
    setBusy(true);
    setError("");
    try {
      const minted = await mintDevToken({
        role,
        actor_id: actor,
        unit_code: unit,
        subject_token: role === "personnel" ? subjectToken || actor : "",
      });
      writeSession({
        token: minted.token,
        role,
        actorId: minted.actor_id,
        subjectToken: role === "personnel" ? subjectToken || actor : "",
        unitCode: unit,
      });
      onReady();
      navigate(homeFor(role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="gate">
      <main className="gate-card">
        <div className="mark" aria-hidden="true" />
        <p className="eyebrow">Uniformed welfare</p>
        <h1>MANOBAL</h1>
        <p className="lede">
          Demonstration consoles on simulated unit data. Identities stay in a separate enclave.
          Nothing on these desks stores a score or a service number.
        </p>
        <ol className="muted walkthrough">
          <li>Personnel — sleep notes, a check-in that can move the picture, Talk, SOS vs helpline.</li>
          <li>Welfare officer — T2 / T3 / T4 with a conversation opener. Category names only.</li>
          <li>Commander — 12BN_A band and a unit briefing. Individuals never appear.</li>
          <li>WDEC — audit trail and break-glass review.</li>
        </ol>
        <p className="muted">
          {llmConfigured
            ? "Talk uses a cloud model. Crisis language never reaches it."
            : "Talk uses a local listener until MANOBAL_LLM_API_KEY is set. Crisis language never reaches a model."}
        </p>
        {error ? <Notice tone="error">{error}</Notice> : null}
        <div className="desk-grid">
          {ROLES.map((item) => (
            <button
              key={item.role}
              type="button"
              className="desk"
              disabled={busy}
              onClick={() =>
                void enter(
                  item.role,
                  item.role === "personnel" ? subjectToken || item.actor : item.actor,
                  item.unit,
                )
              }
            >
              Continue as {item.label}
              <small>
                {item.unit} · {item.desk}
              </small>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
