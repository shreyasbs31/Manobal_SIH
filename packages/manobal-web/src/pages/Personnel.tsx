import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { AgentTurn, Assessment, Checkin, ConsentState, Session } from "../api/types";
import { Notice } from "../components/Notice";

const DATA_TYPES = [
  ["org", "Duty and leave records the force already holds"],
  ["selfreport", "Questionnaires and daily check-ins"],
  ["biometric", "Heart rate, sleep and activity"],
  ["voice_features", "Voice measurements taken on your phone"],
  ["journal", "Private journal entries"],
] as const;

type Props = { session: Session };

export function Personnel({ session }: Props) {
  const api = createClient(session);
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [checkin, setCheckin] = useState<Checkin | null>(null);
  const [error, setError] = useState("");
  const [sos, setSos] = useState(false);
  const [turns, setTurns] = useState<AgentTurn[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    const [nextConsent, nextAssessment, nextCheckin] = await Promise.all([
      api.consent(),
      api.assessment(),
      api.checkin(),
    ]);
    setConsent(nextConsent);
    setAssessment(nextAssessment);
    setCheckin(nextCheckin);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "could not load your record");
    });
  }, [session.token]);

  async function toggle(dataType: string, granted: boolean) {
    await api.setConsent(dataType, granted);
    await refresh();
  }

  async function saveCheckin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.submitCheckin({
      mood: Number(form.get("mood")),
      sleep_quality: Number(form.get("sleep_quality")),
      stress: Number(form.get("stress")),
      connection: Number(form.get("connection")),
      concern_tag: String(form.get("concern_tag") || ""),
    });
    await refresh();
  }

  async function sendAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const turn = await api.agent(message, sessionId || undefined);
    setSessionId(turn.session_id);
    setTurns((current) => [...current, turn]);
    setMessage("");
  }

  return (
    <>
      <h1>Your welfare record</h1>
      <p className="muted">Tier and category names only. No score is stored or shown.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}

      <section className="panel">
        <h2>Current picture</h2>
        <div className={`tier ${assessment?.tier ?? "T0"}`}>{assessment?.tier ?? "—"}</div>
        <p>{assessment?.contributing_categories.join(", ") || "No contributing categories."}</p>
      </section>

      <section className="panel">
        <h2>Consent</h2>
        <p className="muted">Each type is independent. Withdrawal starts erasure for that type.</p>
        {DATA_TYPES.map(([code, label]) => (
          <div className="row" key={code}>
            <span>{label}</span>
            <button type="button" className="ghost" onClick={() => void toggle(code, true)}>
              Grant
            </button>
            <button type="button" className="ghost" onClick={() => void toggle(code, false)}>
              Withdraw
            </button>
            <span className="muted">
              {consent?.consents[code] === true ? "granted" : consent?.consents[code] === false ? "withdrawn" : "unset"}
            </span>
          </div>
        ))}
      </section>

      <section className="panel">
        <h2>Today’s check-in</h2>
        <form className="grid" onSubmit={(event) => void saveCheckin(event)}>
          {(["mood", "sleep_quality", "stress", "connection"] as const).map((field) => (
            <label key={field} htmlFor={field}>
              {field.replace("_", " ")}
              <select id={field} name={field} defaultValue={checkin?.[field] ?? 3} required aria-required="true">
                {[1, 2, 3, 4, 5].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <button type="submit">Save check-in</button>
        </form>
      </section>

      <section className="panel">
        <h2>Need help now</h2>
        <button
          type="button"
          className="danger"
          onClick={() =>
            void api.sos().then(() => {
              setSos(true);
            })
          }
        >
          Send SOS
        </button>
        {sos ? <Notice>Help request accepted. A welfare officer will be notified.</Notice> : null}
      </section>

      <section className="panel">
        <h2>Talk</h2>
        <div className="chat" aria-live="polite">
          {turns.map((turn, index) => (
            <div key={`${turn.session_id}-${index}`} className="bubble">
              {turn.reply}
              {turn.crisis ? " (urgent help has been requested)" : ""}
            </div>
          ))}
        </div>
        <form className="row" onSubmit={(event) => void sendAgent(event)}>
          <label htmlFor="agent-message">
            Message
            <input
              id="agent-message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              required
              aria-required="true"
            />
          </label>
          <button type="submit">Send</button>
        </form>
      </section>
    </>
  );
}
