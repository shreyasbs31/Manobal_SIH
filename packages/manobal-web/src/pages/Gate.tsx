import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { mintDevToken } from "../api/client";
import type { Role } from "../api/types";
import { homeFor, writeSession } from "../auth/session";
import { Notice } from "../components/Notice";

const ROLES: { role: Role; actor: string; unit: string; label: string }[] = [
  { role: "personnel", actor: "tok_seed_0000", unit: "12BN_A", label: "Personnel" },
  { role: "welfare_officer", actor: "officer-001", unit: "12BN", label: "Welfare officer" },
  { role: "medical_officer", actor: "medical-001", unit: "12BN", label: "Medical officer" },
  { role: "commander", actor: "commander-001", unit: "12BN_A", label: "Commander" },
  { role: "wdec_auditor", actor: "wdec-001", unit: "CENTRAL", label: "WDEC auditor" },
];

type Props = {
  subjectToken: string;
  onReady: () => void;
};

export function Gate({ subjectToken, onReady }: Props) {
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
    <main className="main">
      <h1>MANOBAL</h1>
      <p className="muted">Welfare consoles for the analytics plane. No vault lives here.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <div className="grid">
        {ROLES.map((item) => (
          <button
            key={item.role}
            type="button"
            className="ghost"
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
          </button>
        ))}
      </div>
    </main>
  );
}
