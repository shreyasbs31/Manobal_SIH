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
    <ScreenState error={error} loading={loading} offline={offline} empty={!data && !offline}>
      {data || offline ? (
        <div className="mb-home-stack">
          <h1 className="mb-type-title">Assessments</h1>
          <p>
            Short questionnaires on this phone. AUDIT-C never leaves the device. PHQ-9 item 9 opens
            safety if you need it.
          </p>
          {(data?.items ?? [
            {
              id: "pss10",
              title: "PSS-10",
              badge: "self",
              badge_label: "Self-only",
              self_only: true,
              items: 10,
            },
          ]).map((item) => (
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
