import { useEffect, useState } from "react";

import { ApiError, commanderPayloadHasNoToken, createClient } from "../api/client";
import type { Aggregate, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function Commander({ session }: Props) {
  const [unit, setUnit] = useState(session.unitCode || "12BN_A");
  const [aggregate, setAggregate] = useState<Aggregate | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void createClient(session)
      .aggregates(unit)
      .then((body) => {
        if (!commanderPayloadHasNoToken(body)) {
          throw new Error("aggregate contained a subject token");
        }
        setAggregate(body);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "aggregate withheld or unavailable");
      });
  }, [session.token, unit]);

  return (
    <>
      <h1>Unit picture</h1>
      <p className="muted">Bands and category names. Individual tokens never appear here.</p>
      <label htmlFor="unit">
        Unit
        <input id="unit" value={unit} onChange={(event) => setUnit(event.target.value)} />
      </label>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {aggregate?.suppressed ? (
        <Notice>This figure is withheld. The unit is below the k-anonymity threshold or too unstable.</Notice>
      ) : aggregate ? (
        <section className="panel">
          <p>
            Elevated band <strong>{aggregate.elevated_band}</strong>
          </p>
          <p>Dominant category {aggregate.dominant_category || "—"}</p>
          <p>Trend {aggregate.trend_direction || "—"}</p>
        </section>
      ) : null}
    </>
  );
}
