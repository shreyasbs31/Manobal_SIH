import { useEffect, useState } from "react";

import { ApiError, commanderPayloadHasNoToken, createClient } from "../api/client";
import type { Aggregate, Session } from "../api/types";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { humanize } from "../ui/format";

type Props = { session: Session };

export function Commander({ session }: Props) {
  const [unit, setUnit] = useState(session.unitCode || "12BN_A");
  const [aggregate, setAggregate] = useState<Aggregate | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setAggregate(null);
    void createClient(session)
      .aggregates(unit)
      .then((body) => {
        if (!commanderPayloadHasNoToken(body)) {
          throw new Error("aggregate contained a subject token");
        }
        setError("");
        setAggregate(body);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "aggregate withheld or unavailable");
      });
  }, [session.token, unit]);

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Command"
        title="Unit picture"
        lede="Bands and category names. Individual tokens never appear here."
      />
      <form
        className="row"
        onSubmit={(event) => {
          event.preventDefault();
          const next = new FormData(event.currentTarget).get("unit");
          setUnit(String(next || session.unitCode || "12BN_A"));
        }}
      >
        <label htmlFor="unit">
          Unit
          <input id="unit" name="unit" defaultValue={unit} />
        </label>
        <button type="submit">Show</button>
      </form>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {aggregate?.suppressed ? (
        <Notice>This figure is withheld. The unit is below the k-anonymity threshold or too unstable.</Notice>
      ) : aggregate ? (
        <section className="panel">
          <p className="eyebrow">Elevated band</p>
          <div className="tier-mark">
            <span className="tier-code">{aggregate.elevated_band}</span>
            <span className="tier-caption">Elevated band for this unit. No individual tokens.</span>
          </div>
          <div className="stat-row">
            <div className="stat">
              <span className="muted">Dominant category</span>
              <b>{humanize(aggregate.dominant_category || "—")}</b>
            </div>
            <div className="stat">
              <span className="muted">Trend</span>
              <b>{aggregate.trend_direction || "—"}</b>
            </div>
            <div className="stat">
              <span className="muted">Unit</span>
              <b>{aggregate.unit}</b>
            </div>
          </div>
        </section>
      ) : (
        <p className="muted">Loading the unit picture…</p>
      )}
    </div>
  );
}
