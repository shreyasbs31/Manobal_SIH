import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type {
  Assessment,
  ConsentLedgerEntry,
  ConsentState,
  ErasureReceipt,
  HelplineCard,
  Insights,
  OwnTrends,
  Session,
} from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { NextActions } from "../components/NextActions";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { TierMark } from "../components/TierMark";
import { WeekStrip } from "../components/WeekStrip";
import { personnelCopy, readPersonnelLang, storePersonnelLang, type PersonnelLang } from "../i18n/personnel";
import {
  appendListener,
  appendYou,
  crisisNotice,
  prepareTalk,
  type ChatLine,
} from "../talk";
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
  ["transcript_edge", "Your words sent to the unit server (Tier B devices only)"],
] as const;

const CHECKIN_FIELDS = [
  ["mood", "Mood", ["Very low", "Low", "Okay", "Good", "Strong"]],
  ["sleep_quality", "Sleep", ["Broken", "Thin", "Fair", "Solid", "Rested"]],
  ["stress", "Stress", ["Calm", "Mild", "Steady", "High", "Wired"]],
  ["fatigue", "Fatigue", ["Fresh", "Tired", "Worn", "Heavy", "Spent"]],
  ["connection", "Connection", ["Alone", "Distant", "Some", "Close", "Held"]],
] as const;

type CheckField = (typeof CHECKIN_FIELDS)[number][0];

type Props = { session: Session };

export function Personnel({ session }: Props) {
  const api = createClient(session);
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [sos, setSos] = useState(false);
  const [helpline, setHelpline] = useState<HelplineCard | null>(null);
  const [ledger, setLedger] = useState<ConsentLedgerEntry[]>([]);
  const [erasures, setErasures] = useState<ErasureReceipt[]>([]);
  const [trends, setTrends] = useState<OwnTrends | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [checkValues, setCheckValues] = useState({
    mood: 3,
    sleep_quality: 3,
    stress: 3,
    fatigue: 3,
    connection: 3,
    concern_tag: "",
  });
  const [lang, setLang] = useState<PersonnelLang>(readPersonnelLang);
  const copy = personnelCopy(lang);

  async function refresh() {
    const [nextConsent, nextAssessment, todayCheckin, nextLedger, nextErasure, nextTrends, nextInsights] =
      await Promise.all([
        api.consent(),
        api.assessment(),
        api.checkin(),
        api.consentLedger(),
        api.erasure(),
        api.trends(),
        api.insights(),
      ]);
    setConsent(nextConsent);
    setAssessment(nextAssessment);
    setLedger(nextLedger.entries);
    setErasures(nextErasure.requests);
    setTrends(nextTrends);
    setInsights(nextInsights);
    try {
      setHelpline(await api.helpline());
    } catch {
      /* helplines stay hidden until the next successful load */
    }
    setCheckValues({
      mood: todayCheckin.mood ?? 3,
      sleep_quality: todayCheckin.sleep_quality ?? 3,
      stress: todayCheckin.stress ?? 3,
      fatigue: todayCheckin.fatigue ?? 3,
      connection: todayCheckin.connection ?? 3,
      concern_tag: todayCheckin.concern_tag ?? "",
    });
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
    try {
      const saved = await api.submitCheckin({
        mood: checkValues.mood,
        sleep_quality: checkValues.sleep_quality,
        stress: checkValues.stress,
        fatigue: checkValues.fatigue,
        connection: checkValues.connection,
        concern_tag: checkValues.concern_tag,
      });
      setError("");
      if (saved.picture_changed && saved.tier && saved.previous_tier) {
        setSaved(`${copy.pictureMoved} ${saved.previous_tier} → ${saved.tier}.`);
      } else if (saved.picture_changed && saved.tier) {
        setSaved(`${copy.pictureMoved} ${saved.tier}.`);
      } else {
        setSaved(copy.pictureSame);
      }
      if (saved.insights) {
        setInsights(saved.insights);
      }
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not save the check-in");
    }
  }

  async function sendAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = prepareTalk(message);
    if (next.kind === "empty") {
      return;
    }
    if (next.kind === "crisis") {
      setLines((current) => appendListener(appendYou(current, next.message, true), crisisNotice(), true));
      setMessage("");
      setError("");
      try {
        await api.sos();
        setSos(true);
      } catch (err: unknown) {
        setError(err instanceof ApiError ? err.message : "could not send the SOS");
      }
      return;
    }
    setBusy(true);
    setError("");
    setLines((current) => appendYou(current, next.message));
    setMessage("");
    try {
      const turn = await api.agent(next.message, sessionId || undefined);
      setSessionId(turn.session_id);
      setLines((current) => appendListener(current, turn.reply, turn.crisis));
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not send the message");
    } finally {
      setBusy(false);
    }
  }

  async function startErasure(dataType: string) {
    try {
      await api.requestErasure(dataType);
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not start erasure");
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
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} lede={copy.lede} />
      <div className="actions">
        <label htmlFor="personnel-lang">
          {copy.language}
          <select
            id="personnel-lang"
            value={lang}
            onChange={(event) => {
              const next = event.target.value === "hi" ? "hi" : "en";
              setLang(next);
              storePersonnelLang(next);
            }}
          >
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
          </select>
        </label>
      </div>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <nav className="page-jump" aria-label="On this page">
        <a href="#picture">Picture</a>
        <a href="#checkin">Check-in</a>
        <a href="#talk">Talk</a>
        <a href="#help">Help</a>
        <a href="#journal">Journal</a>
        <a href="#instruments">Questionnaires</a>
      </nav>

      <section className="panel" id="picture">
        <h2>{copy.picture}</h2>
        <TierMark tier={assessment?.tier} />
        {insights?.lede ? <p className="lede-call">{insights.lede}</p> : null}
        <p>{categoryList(assessment?.contributing_categories ?? [])}</p>
        {insights?.streak ? (
          <p className="muted">
            {copy.streak}: {insights.streak === 1 ? "1 day" : `${insights.streak} days`}
          </p>
        ) : null}
        {assessment?.why?.length ? (
          <div>
            <h3>{copy.why}</h3>
            <ul>
              {assessment.why.map((row) => (
                <li key={row.category}>{row.meaning}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {insights?.notes.length ? (
          <ul className="note-list">
            {insights.notes.map((note) => (
              <li key={note.field}>{note.text}</li>
            ))}
          </ul>
        ) : null}
        {insights?.settled_low && insights.settled_message ? (
          <Notice>{insights.settled_message}</Notice>
        ) : null}
        {insights?.engine_note ? (
          <p className="note">
            <strong>{copy.engine}.</strong> {insights.engine_note}
          </p>
        ) : null}
        {insights?.next.length ? (
          <>
            <h3>{copy.next}</h3>
            <NextActions items={insights.next} />
          </>
        ) : null}
        {assessment?.acute_override ? <p className="muted">An acute override is in force.</p> : null}
        {assessment?.offer_checkin ? (
          <Notice>
            Extra check-in offered after a unit incident
            {assessment.incident_category ? ` (${assessment.incident_category})` : ""}. This is
            optional and is not itself a flag.
          </Notice>
        ) : null}
      </section>

      <section className="panel" id="checkin">
        <h2>{copy.checkin}</h2>
        {saved ? <Notice>{saved}</Notice> : null}
        <form onSubmit={(event) => void saveCheckin(event)}>
          {CHECKIN_FIELDS.map(([field, label, words]) => (
            <ScaleRow
              key={field}
              field={field}
              label={label}
              words={words}
              value={checkValues[field]}
              onChange={(value) => setCheckValues((current) => ({ ...current, [field]: value }))}
            />
          ))}
          <label htmlFor="concern_tag">
            Optional concern
            <input
              id="concern_tag"
              name="concern_tag"
              value={checkValues.concern_tag}
              onChange={(event) =>
                setCheckValues((current) => ({ ...current, concern_tag: event.target.value }))
              }
            />
          </label>
          <div className="span">
            <button type="submit">Save check-in</button>
          </div>
        </form>
      </section>

      <section className="panel" id="talk">
        <h2>{copy.talk}</h2>
        <p className="muted">{copy.talkHint}</p>
        <div className="chat" aria-live="polite">
          {lines.length ? (
            lines.map((line) => (
              <div key={line.id} className={line.role === "you" ? "bubble you" : "bubble"}>
                <strong>{line.role === "you" ? "You" : "Listener"}</strong>
                <p>{line.text}</p>
              </div>
            ))
          ) : (
            <EmptyState title="No conversation yet">Write in your own words. This is not scored.</EmptyState>
          )}
          {busy ? <p className="muted">{copy.thinking}</p> : null}
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
              disabled={busy}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? copy.thinking : "Send"}
          </button>
        </form>
      </section>

      <section className="panel" id="help">
        <h2>{copy.help}</h2>
        <p className="muted">{copy.helplineHint}</p>
        <div className="actions">
          <button type="button" className="danger" onClick={() => void sendSos()}>
            {copy.sos}
          </button>
        </div>
        {helpline ? (
          <ul>
            {Object.entries(helpline.helplines)
              .filter(([, number]) => number)
              .map(([name, number]) => (
                <li key={name}>
                  <a href={`tel:${number}`}>
                    {name.replaceAll("_", " ")} · {number}
                  </a>
                </li>
              ))}
          </ul>
        ) : null}
        {helpline ? <p className="muted">Recorded: {String(helpline.recorded)}</p> : null}
        {sos ? <Notice>Help request accepted. A welfare officer will be notified.</Notice> : null}
      </section>

      <section className="panel">
        <h2>{copy.consent}</h2>
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
        <h2>{copy.trends}</h2>
        <p className="muted">Your own check-ins only. No welfare score is stored or shown.</p>
        {trends?.checkins.length ? (
          <>
            <WeekStrip points={trends.checkins} />
            <ul>
              {trends.checkins.slice(0, 7).map((row) => (
                <li key={row.observed_on}>
                  {row.observed_on}: mood {row.mood ?? "—"} · sleep {row.sleep_quality ?? "—"} ·
                  fatigue {row.fatigue ?? "—"}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <EmptyState title="No check-ins yet">Save today’s check-in to start a private trend.</EmptyState>
        )}
      </section>

      <section className="panel">
        <h2>{copy.ledger}</h2>
        <p className="muted">Every grant and withdrawal is kept. Silence is not consent.</p>
        {ledger.length ? (
          <ul>
            {ledger.slice(0, 12).map((row) => (
              <li key={`${row.data_type}-${row.recorded_at}`}>
                {row.data_type} · {row.granted ? "granted" : "withdrawn"} · {row.recorded_at}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No ledger rows yet">Grant or withdraw a data type to write the first entry.</EmptyState>
        )}
        <div className="actions">
          <button type="button" className="ghost" onClick={() => void startErasure("journal")}>
            Erase journal
          </button>
        </div>
        {erasures.length ? (
          <ul>
            {erasures.map((row) => (
              <li key={row.id}>
                Erasure {row.id} [{row.status}]
                {row.receipt_id ? ` · receipt ${row.receipt_id}` : ""}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <PersonnelJournal session={session} />
      <PersonnelInstruments session={session} />
      <PersonnelCases session={session} />
      <PersonnelDevices session={session} />
    </div>
  );
}

function ScaleRow({
  label,
  words,
  value,
  onChange,
}: {
  field: CheckField;
  label: string;
  words: readonly string[];
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <fieldset className="scale">
      <legend>{label}</legend>
      <p className="scale-word">{words[value - 1] ?? ""}</p>
      <div className="scale-row" role="group" aria-label={label}>
        {[1, 2, 3, 4, 5].map((score) => {
          const on = value === score;
          return (
            <button
              key={score}
              type="button"
              className={on ? "scale-chip on" : "scale-chip"}
              aria-pressed={on}
              aria-label={`${label} ${score}, ${words[score - 1] ?? ""}`}
              onClick={() => onChange(score)}
            >
              {score}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
