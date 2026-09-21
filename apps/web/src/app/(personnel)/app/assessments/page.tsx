"use client";

import { ValidatedBadge } from "@manobal/ui";
import Link from "next/link";

import { ScreenState } from "@/components/screen-state";
import { assessmentTitle } from "@/lib/assessment-titles";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function AssessmentsPage() {
  const { p } = usePersonnelI18n();
  const { data, error, loading, offline } = useEngine("assessments", (client, signal) =>
    client.meAssessments(signal),
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data && !offline}>
      {data || offline ? (
        <div className="mb-home-stack">
          <p>{p("A few short questions. Answers stay with you unless you ask for help.")}</p>
          {(data?.items ?? [
            {
              id: "pss10",
              title: "How you've been feeling",
              badge: "self",
              badge_label: "Self-only",
              self_only: true,
              items: 10,
            },
          ]).map((item) => (
            <article className="mb-instrument" key={item.id}>
              <div>
                <h2>{p(assessmentTitle(item.id, item.title))}</h2>
                <p>{p(item.self_only ? "Stays on this phone" : "Optional")}</p>
                {item.self_only ? (
                  <span className="mb-self-only">{p("Self-only")}</span>
                ) : (
                  <ValidatedBadge label={p("Validated translation")} />
                )}
              </div>
              <Link className="mb-primary" href={`/app/assessments/${item.id}`}>
                {p("Open")}
              </Link>
            </article>
          ))}
        </div>
      ) : null}
    </ScreenState>
  );
}
