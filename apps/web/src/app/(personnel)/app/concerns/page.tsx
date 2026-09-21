"use client";

import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function ConcernsPage() {
  const { p } = usePersonnelI18n();
  const { data, error, loading, offline, reload } = useEngine("concerns", (client, signal) =>
    client.meConcerns(signal),
  );
  const [category, setCategory] = useState("leave");
  const [text, setText] = useState("");
  const [anonymous, setAnonymous] = useState(false);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={false}>
      <div className="mb-home-stack">
        <p>{p("Leave, land, family, or colleagues. You can send this without your name.")}</p>
        <label>
          {p("Category")}
          <select onChange={(event) => setCategory(event.target.value)} value={category}>
            <option value="leave">{p("Leave")}</option>
            <option value="land">{p("Land or property")}</option>
            <option value="family">{p("Family")}</option>
            <option value="colleagues">{p("Colleagues")}</option>
            <option value="other">{p("Other")}</option>
          </select>
        </label>
        <label>
          {p("What happened")}
          <textarea onChange={(event) => setText(event.target.value)} value={text} />
        </label>
        <label className="mb-check-row">
          <input
            checked={anonymous}
            onChange={(event) => setAnonymous(event.target.checked)}
            type="checkbox"
          />
          {p("Send without my name")}
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
          {p("Send")}
        </button>
        <h2 className="mb-section-label">{p("Status")}</h2>
        {(data?.items ?? []).length === 0 ? (
          <p>{p("No concerns sent yet.")}</p>
        ) : (
          (data?.items ?? []).map((row) => (
            <article className="mb-card" key={String(row.id)}>
              <h2>{p(String(row.category))}</h2>
              <p>
                {p(String(row.status))}
                {row.sla ? ` · ${p("due {date}", { date: String(row.sla) })}` : ""}
                {row.anonymous ? ` · ${p("sent without your name")}` : ""}
              </p>
            </article>
          ))
        )}
      </div>
    </ScreenState>
  );
}
