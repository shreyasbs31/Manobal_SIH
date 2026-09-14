import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createClient } from "../api/client";
import type { CaseSummary, OfficerDestination, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { categoryList, formatWhen, shortToken } from "../ui/format";

type Props = { session: Session };

export function OfficerQueue({ session }: Props) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [destination, setDestination] = useState<OfficerDestination | null>(null);
  const [error, setError] = useState("");
  const api = createClient(session);

  useEffect(() => {
    void Promise.all([api.queue(), api.officerDestination()])
      .then(([body, dest]) => {
        setCases(body.cases);
        setDestination(dest);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "queue unavailable");
        setCases([]);
      });
  }, [session.token]);

  async function saveDestination(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const phone = String(form.get("duty_phone_e164") || "").trim();
      const token = String(form.get("push_token") || "").trim();
      const next = await api.setOfficerDestination({
        ...(phone ? { duty_phone_e164: phone } : {}),
        ...(token ? { push_token: token } : {}),
      });
      setDestination(next);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not save destination");
    }
  }

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Welfare officer"
        title="Assigned cases"
        lede="Tokens and category names only. There is no score on this board."
      />
      {error ? <Notice tone="error">{error}</Notice> : null}
      <section className="panel">
        <h2>How you are reached</h2>
        <p className="muted">
          Alerts go to this duty phone and this device. A subject number is never stored here.
        </p>
        <form className="grid" onSubmit={(event) => void saveDestination(event)}>
          <label htmlFor="duty_phone_e164">
            Duty phone (E.164)
            <input
              id="duty_phone_e164"
              name="duty_phone_e164"
              placeholder={destination?.duty_phone_set ? `ending ${destination.duty_phone_hint}` : "+91…"}
            />
          </label>
          <label htmlFor="push_token">
            Push token
            <input
              id="push_token"
              name="push_token"
              placeholder={destination?.push_token_set ? "token on file" : "FCM registration token"}
            />
          </label>
          <button type="submit">Save destination</button>
        </form>
      </section>
      {!cases ? (
        <p className="muted">Loading the queue…</p>
      ) : !cases.length ? (
        <EmptyState title="No assigned cases">Open flags in your unit will appear here with a due time.</EmptyState>
      ) : (
        <section className="case-grid">
          {cases.map((item) => (
            <article key={item.id} className={`case-card tier-${item.tier}`}>
              <div className="case-card-top">
                <span className={`pill ${item.tier === "T4" ? "bad" : item.tier === "T3" ? "warn" : ""}`}>
                  {item.tier}
                </span>
                <span className="muted">{formatWhen(item.sla_due_at)}</span>
              </div>
              <Link to={`/officer/cases/${item.id}`}>Open case {item.id}</Link>
              {item.headline ? <p className="headline">{item.headline}</p> : null}
              <p>{categoryList(item.contributing_categories)}</p>
              <p className="muted mono">{shortToken(item.subject_token)}</p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
