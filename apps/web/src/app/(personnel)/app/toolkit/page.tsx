"use client";

import { SceneEmptyPath, SceneSleepWindDown } from "@manobal/illustrations";
import Link from "next/link";

import { ScreenState } from "@/components/screen-state";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function ToolkitPage() {
  const { p } = usePersonnelI18n();
  const { data, error, loading, offline } = useEngine("toolkit", (client, signal) =>
    client.meToolkit(signal),
  );

  const items = data?.items ?? [
    {
      id: "breathe",
      title: "Box breathing",
      detail: "Four counts in, hold, out, hold.",
      href: "/app/toolkit/breathe",
      offline: true,
    },
    {
      id: "grounding",
      title: "5-4-3-2-1 grounding",
      detail: "Name what you can see, feel, and hear.",
      href: "/app/toolkit/grounding",
      offline: true,
    },
  ];

  return (
    <ScreenState error={error} loading={loading && !offline} offline={offline} empty={false}>
        <div className="mb-home-stack">
          <p>{p("Short practices that stay on this phone.")}</p>
        {items.map((item, index) => (
          <article className="mb-context-card" key={item.id}>
            {index === 0 ? <SceneSleepWindDown /> : <SceneEmptyPath />}
            <div>
              <h2>{p(item.title)}</h2>
              <p>{p(item.detail)}</p>
              {item.offline ? <p>{p("Works without a network.")}</p> : null}
              <div className="mb-action-row">
                <Link className="mb-primary" href={item.href}>
                  {p("Start")}
                </Link>
              </div>
            </div>
          </article>
        ))}
      </div>
    </ScreenState>
  );
}
