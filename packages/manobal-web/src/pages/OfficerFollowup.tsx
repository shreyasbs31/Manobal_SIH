import { FormEvent, useState } from "react";

import { createClient } from "../api/client";
import type { Session, TrendPoint } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session; caseId: number };

export function OfficerFollowup({ session, caseId }: Props) {
  const api = createClient(session);
  const [points, setPoints] = useState<TrendPoint[] | null>(null);
  const [notice, setNotice] = useState("");

  async function onDisclosure(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.requestDisclosure(
      caseId,
      String(form.get("category")),
      String(form.get("rationale")),
    );
    setNotice("Disclosure requested. Nothing is visible until the person grants it.");
  }

  async function onTrend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = await api.categoryTrend(caseId, String(form.get("trend_category")));
    setPoints(body.points);
  }

  async function onRefer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await api.referClinical(
      caseId,
      String(form.get("medical_actor_id")),
      String(form.get("clinical_rationale")),
    );
    setNotice(`Clinical grant ${result.grant_id} opened. The medical officer is not the assignee.`);
  }

  return (
    <>
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
          <ul>
            {points.map((point) => (
              <li key={point.assessed_at}>
                {point.assessed_at} · {point.present ? "present" : "absent"}
              </li>
            ))}
          </ul>
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
