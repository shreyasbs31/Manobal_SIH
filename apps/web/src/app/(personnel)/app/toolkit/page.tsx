"use client";

import { SceneEmptyPath, SceneSleepWindDown } from "@manobal/illustrations";
import Link from "next/link";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function ToolkitPage() {
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
        <h2 className="mb-type-title">Toolkit</h2>
        <p>
          Breathing, rest, letters, and short reads stay on this phone. Nothing here is sent to a
          commander. Open one and follow the steps. Helped or not for me only changes the order for
          you.
        </p>
        {items.map((item, index) => (
          <article className="mb-context-card" key={item.id}>
            {index === 0 ? <SceneSleepWindDown /> : <SceneEmptyPath />}
            <div>
              <h2>{item.title}</h2>
              <p>{item.detail}</p>
              {item.offline ? <p>Works without a network.</p> : null}
              <Link className="mb-primary" href={item.href}>
                Start
              </Link>
            </div>
          </article>
        ))}
      </div>
    </ScreenState>
  );
}
