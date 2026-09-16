import { SceneEmptyPath } from "@manobal/illustrations";
import Link from "next/link";

export default function ToolkitPage() {
  return (
    <div className="mb-home-stack">
      <h1 className="mb-type-title">Toolkit</h1>
      <p>Breathing and rest guides work without a network.</p>
      <article className="mb-context-card">
        <SceneEmptyPath />
        <div>
          <h2>Box breathing</h2>
          <p>A four-count cycle. Two minutes. Haptic on each phase.</p>
          <Link className="mb-primary" href="/app/toolkit/breathe">
            Start
          </Link>
        </div>
      </article>
    </div>
  );
}
