"use client";

import { SceneEmptyPath, SceneSleepWindDown } from "@manobal/illustrations";
import Link from "next/link";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function ToolkitPage() {
  const { data, error, loading, offline } = useEngine("toolkit", (client, signal) =>
    client.meToolkit(signal),
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <h2 className="mb-type-title">Toolkit</h2>
          <p>Breathing, rest, and short reads work without a network.</p>
          {data.items.map((item, index) => (
            <article className="mb-context-card" key={item.id}>
              {index === 0 ? <SceneSleepWindDown /> : <SceneEmptyPath />}
              <div>
                <h2>{item.title}</h2>
                <p>{item.detail}</p>
                <Link className="mb-primary" href={item.href}>
                  Start
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </ScreenState>
  );
}
