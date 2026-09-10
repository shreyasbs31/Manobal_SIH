import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { AgentTurn, Assessment, Checkin, ConsentState, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { TierMark } from "../components/TierMark";
import { categoryList, consentLabel } from "../ui/format";
import { PersonnelCases } from "./PersonnelCases";
import { PersonnelDevices } from "./PersonnelDevices";
import { PersonnelInstruments } from "./PersonnelInstruments";
import { PersonnelJournal } from "./PersonnelJournal";

const DATA_TYPES = [
  ["org", "Duty and leave records the force already holds"],
  ["selfreport", "Questionnaires and daily check-ins"],
  ["biometric", "Heart rate, sleep and activity"],
  ["voice_features", "Voice measurements taken on your phone"],
  ["journal", "Private journal entries"],
] as const;

const CHECKIN_FIELDS = [
  ["mood", "Mood"],
  ["sleep_quality", "Sleep"],
  ["stress", "Stress"],
  ["connection", "Connection"],
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
    try {
      await api.setConsent(dataType, granted);
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not update consent");
    }
  }

  async function saveCheckin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.submitCheckin({
        mood: Number(form.get("mood")),
        sleep_quality: Number(form.get("sleep_quality")),
        stress: Number(form.get("stress")),
        connection: Number(form.get("connection")),
        concern_tag: String(form.get("concern_tag") || ""),
      });
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not save the check-in");
    }
  }

  async function sendAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const turn = await api.agent(message, sessionId || undefined);
      setError("");
      setSessionId(turn.session_id);
      setTurns((current) => [...current, turn]);
      setMessage("");
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not send the message");
    }
  }

  async function sendSos() {
    try {
      await api.sos();
      setError("");
      setSos(true);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not send the SOS");
    }
  }

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Personnel desk"
        title="Your welfare record"
        lede="Tier and category names only. No score is stored or shown."
      />
      {error ? <Notice tone="error">{error}</Notice> : null}

      <section className="panel">
        <h2>Current picture</h2>
        <TierMark tier={assessment?.tier} />
        <p>{categoryList(assessment?.contributing_categories ?? [])}</p>
        {assessment?.acute_override ? <p className="muted">An acute override is in force.</p> : null}
      </section>

      <section className="panel">
        <h2>Consent</h2>
        <p className="muted">Each type is independent. Withdrawal starts erasure for that type.</p>
        <div className="ledger">
          {DATA_TYPES.map(([code, label]) => {
            const state = consentLabel(consent?.consents[code]);
            return (
              <div className="ledger-row" key={code}>
                <div>
                  <strong>{label}</strong>
                  <div>
                    <span className={`pill ${state === "granted" ? "ok" : state === "withdrawn" ? "bad" : ""}`}>
                      {state}
                    </span>
                  </div>
                </div>
                <div className="actions">
                  <button type="button" className="ghost" onClick={() => void toggle(code, true)}>
                    Grant
                  </button>
                  <button type="button" className="ghost" onClick={() => void toggle(code, false)}>
                    Withdraw
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="panel">
        <h2>Today’s check-in</h2>
        <form className="grid two" key={checkin?.observed_on ?? "blank"} onSubmit={(event) => void saveCheckin(event)}>
          {CHECKIN_FIELDS.map(([field, label]) => (
            <label key={field} htmlFor={field}>
              {label}
              <select id={field} name={field} defaultValue={checkin?.[field] ?? 3} required aria-required="true">
                {[1, 2, 3, 4, 5].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <label htmlFor="concern_tag">
            Optional concern
            <input id="concern_tag" name="concern_tag" defaultValue={checkin?.concern_tag ?? ""} />
          </label>
          <div className="span">
            <button type="submit">Save check-in</button>
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Need help now</h2>
        <p className="muted">This notifies a welfare officer. It does not send your journal.</p>
        <button type="button" className="danger" onClick={() => void sendSos()}>
          Send SOS
        </button>
        {sos ? <Notice>Help request accepted. A welfare officer will be notified.</Notice> : null}
      </section>

      <section className="panel">
        <h2>Talk</h2>
        <div className="chat" aria-live="polite">
          {turns.length ? (
            turns.map((turn, index) => (
              <div key={`${turn.session_id}-${index}`} className="bubble">
                {turn.reply}
                {turn.crisis ? " (urgent help has been requested)" : ""}
              </div>
            ))
          ) : (
            <EmptyState title="No conversation yet">Write in your own words. This is not scored.</EmptyState>
          )}
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

      <PersonnelJournal session={session} />
      <PersonnelInstruments session={session} />
      <PersonnelCases session={session} />
      <PersonnelDevices session={session} />
    </div>
  );
}
