"use client";

import { useState } from "react";

export function EmojiScale({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  const faces = ["😞", "🙁", "😐", "🙂", "😊"] as const;
  return (
    <fieldset className="mb-emoji">
      <legend>{label}</legend>
      <div className="mb-emoji-row">
        {faces.map((face, index) => {
          const score = index + 1;
          return (
            <button
              aria-label={`${label} ${score} of 5`}
              aria-pressed={value === score}
              key={face}
              onClick={() => onChange(score)}
              type="button"
            >
              <span aria-hidden="true">{face}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export interface LanguageOption {
  tag: string;
  label: string;
  direction: "ltr" | "rtl";
}

export function LanguageGrid({
  languages,
  value,
  onChange,
}: {
  languages: readonly LanguageOption[];
  value: string;
  onChange: (tag: string) => void;
}) {
  return (
    <div className="mb-lang-grid">
      {languages.map((language) => (
        <button
          aria-pressed={value === language.tag}
          dir={language.direction}
          key={language.tag}
          lang={language.tag}
          onClick={() => onChange(language.tag)}
          type="button"
        >
          {language.label}
        </button>
      ))}
    </div>
  );
}

export function SafetyPlanEditor() {
  const [warning, setWarning] = useState("Sleep dropping, shorter replies");
  const [coping, setCoping] = useState("Box breathing, walk the perimeter");
  const [people, setPeople] = useState("Buddy, counsellor desk");
  return (
    <form className="mb-card mb-safety">
      <label>
        Warning signs I notice
        <textarea
          onChange={(event) => setWarning(event.target.value)}
          value={warning}
        />
      </label>
      <label>
        What helps me
        <textarea
          onChange={(event) => setCoping(event.target.value)}
          value={coping}
        />
      </label>
      <label>
        People I can reach
        <textarea
          onChange={(event) => setPeople(event.target.value)}
          value={people}
        />
      </label>
    </form>
  );
}

export function LeaveWindowPicker() {
  return (
    <form className="mb-card mb-leave">
      <label>
        Suggested window start
        <input defaultValue="2026-10-04" type="date" />
      </label>
      <label>
        Suggested window end
        <input defaultValue="2026-10-12" type="date" />
      </label>
      <p>Unit blackout windows are shown at unit level only. MANOBAL does not submit leave.</p>
    </form>
  );
}

export function ShiftTimeline({
  days,
}: {
  days: readonly { label: string; start: number; end: number }[];
}) {
  return (
    <div className="mb-shift" aria-label="Shift timeline">
      {days.map((day) => (
        <div className="mb-shift-row" key={day.label}>
          <span>{day.label}</span>
          <div className="mb-shift-bar">
            <span
              className="mb-shift-fill"
              style={{
                insetInlineStart: `${day.start}%`,
                width: `${Math.max(day.end - day.start, 8)}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
