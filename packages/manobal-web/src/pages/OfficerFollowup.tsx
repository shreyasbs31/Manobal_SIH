import { FormEvent, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { Session, TrendPoint } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { formatWhen } from "../ui/format";

type Props = { session: Session; caseId: number };

export function OfficerFollowup({ session, caseId }: Props) {
  const api = createClient(session);
  const [points, setPoints] = useState<TrendPoint[] | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function onDisclosure(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.requestDisclosure(
        caseId,
        String(form.get("category")),
        String(form.get("rationale")),
      );
      setError("");
      setNotice("Disclosure requested. Nothing is visible until the person grants it.");
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not request disclosure");
    }
  }

  async function onTrend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const body = await api.categoryTrend(caseId, String(form.get("trend_category")));
      setError("");
      setPoints(body.points);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "trend is not available");
    }
  }

  async function onRefer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api.referClinical(
        caseId,
        String(form.get("medical_actor_id")),
        String(form.get("clinical_rationale")),
      );
      setError("");
      setNotice(`Clinical grant ${result.grant_id} opened. The medical officer is not the assignee.`);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "referral refused");
    }
  }

  return (
    <>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {notice ? <Notice>{notice}</Notice> : null}
      <section className="panel">
        <h2>Ask for a category trend</h2>
        <form className="grid" onSubmit={(event) => void onDisclosure(event)}>
          <label htmlFor="category">
            Category
            <input id="category" name="category" required aria-required="true" />
          </label>
          <label htmlFor="rationale">
            Why
            <textarea id="rationale" name="rationale" required aria-required="true" rows={2} />
          </label>
          <button type="submit">Request disclosure</button>
        </form>
        <form className="row" onSubmit={(event) => void onTrend(event)}>
          <label htmlFor="trend_category">
            Open a granted trend
            <input id="trend_category" name="trend_category" required aria-required="true" />
          </label>
          <button type="submit">Show presence</button>
        </form>
        {points ? (
          points.length ? (
            <ul>
              {points.map((point) => (
                <li key={point.assessed_at}>
                  {formatWhen(point.assessed_at)} · {point.present ? "present" : "absent"}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No points in this window">Presence only. No scores are shown.</EmptyState>
          )
        ) : null}
      </section>
      <section className="panel">
        <h2>Refer to a medical officer</h2>
        <p className="muted">T3 and T4 only. They receive a grant, not the case.</p>
        <form className="grid" onSubmit={(event) => void onRefer(event)}>
          <label htmlFor="medical_actor_id">
            Medical officer
            <input id="medical_actor_id" name="medical_actor_id" defaultValue="medical-001" required aria-required="true" />
          </label>
          <label htmlFor="clinical_rationale">
            Rationale
            <textarea id="clinical_rationale" name="clinical_rationale" required aria-required="true" rows={2} />
          </label>
          <button type="submit">Refer</button>
        </form>
      </section>
    </>
  );
}
