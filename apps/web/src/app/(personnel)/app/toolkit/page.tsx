import { EmptyState } from "@manobal/ui";

export default function ToolkitPage() {
  return (
    <div className="mb-home-stack">
      <h1>Toolkit</h1>
      <p>Breathing, grounding, and rest guides work without a network.</p>
      <article className="mb-card">
        <h2>Box breathing</h2>
        <p>Four counts in, hold, out, hold. Two minutes.</p>
        <button className="mb-primary" type="button">
          Start
        </button>
      </article>
      <EmptyState
        message="Audio guides for other languages will appear here when they are cached."
        title="More guides"
      />
    </div>
  );
}
