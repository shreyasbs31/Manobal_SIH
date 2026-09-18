"use client";

import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function ConcernsPage() {
  const { data, error, loading, offline, reload } = useEngine("concerns", (client, signal) =>
    client.meConcerns(signal),
  );
  const [category, setCategory] = useState("leave");
  const [text, setText] = useState("");
  const [anonymous, setAnonymous] = useState(false);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={false}>
      <div className="mb-home-stack">
        <h1 className="mb-type-title">Raise a concern</h1>
        <p>
          Leave, land, family, or colleagues. Welfare sees the category and your words, not a score.
          You can send it without your name.
        </p>
        <label>
          Category
          <select onChange={(event) => setCategory(event.target.value)} value={category}>
            <option value="leave">Leave</option>
            <option value="land">Land or property</option>
            <option value="family">Family</option>
            <option value="colleagues">Colleagues</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>
          What happened
          <textarea onChange={(event) => setText(event.target.value)} value={text} />
        </label>
        <label className="mb-check-row">
          <input
            checked={anonymous}
            onChange={(event) => setAnonymous(event.target.checked)}
            type="checkbox"
          />
          Send without my name
        </label>
        <button
          className="mb-primary"
          onClick={() => {
            if (!text.trim()) {
              return;
            }
            void engineClient()
              .saveConcern({ category, text, anonymous })
              .then(() => {
                setText("");
                reload();
              });
          }}
          type="button"
        >
          Send
        </button>
        <h2 className="mb-section-label">Status</h2>
        {(data?.items ?? []).length === 0 ? (
          <p>No concerns sent yet.</p>
        ) : (
          (data?.items ?? []).map((row) => (
            <article className="mb-card" key={String(row.id)}>
              <h2>{String(row.category)}</h2>
              <p>
                {String(row.status)} · SLA {String(row.sla)}
                {row.anonymous ? " · sent without your name" : ""}
              </p>
            </article>
          ))
        )}
      </div>
    </ScreenState>
  );
}
