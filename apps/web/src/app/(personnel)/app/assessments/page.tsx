"use client";

import { ValidatedBadge } from "@manobal/ui";
import Link from "next/link";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function AssessmentsPage() {
  const { data, error, loading, offline } = useEngine("assessments", (client, signal) =>
    client.meAssessments(signal),
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <h1 className="mb-type-title">Assessments</h1>
          {data.items.map((item) => (
            <article className="mb-instrument" key={item.id}>
              <div>
                <h2>{item.title}</h2>
                <p>Due {item.badge_label === "Self-only" ? "anytime, on this phone" : "optional"}</p>
                {item.self_only ? (
                  <span className="mb-self-only">Self-only</span>
                ) : (
                  <ValidatedBadge />
                )}
              </div>
              <Link className="mb-primary" href={`/app/assessments/${item.id}`}>
                Open
              </Link>
            </article>
          ))}
        </div>
      ) : null}
    </ScreenState>
  );
}
