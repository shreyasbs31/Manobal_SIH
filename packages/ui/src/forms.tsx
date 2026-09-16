"use client";

import { useState } from "react";

import { tickCheckIn } from "./sound.mjs";

const FACE_LABELS = [
  "Very low",
  "Low",
  "Okay",
  "Good",
  "Very good",
] as const;

function Face({ score }: { score: number }) {
  const mouth =
    score === 1
      ? "M8 16 Q12 13 16 16"
      : score === 2
        ? "M8 15.5 Q12 14 16 15.5"
        : score === 3
          ? "M8 15.5 H16"
          : score === 4
            ? "M8 15 Q12 17 16 15"
            : "M8 14.5 Q12 18 16 14.5";
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="mb-face">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="9" cy="10" r="1.1" fill="currentColor" />
      <circle cx="15" cy="10" r="1.1" fill="currentColor" />
      <path d={mouth} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function FaceScale({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <fieldset className="mb-emoji">
      <legend>{label}</legend>
      <div className="mb-emoji-row">
        {FACE_LABELS.map((faceLabel, index) => {
          const score = index + 1;
          return (
            <button
              aria-label={`${label} ${faceLabel}`}
              aria-pressed={value === score}
              key={faceLabel}
              onClick={() => {
                tickCheckIn();
                onChange(score);
              }}
              type="button"
            >
              <Face score={score} />
              <span>{faceLabel}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function EmojiScale(props: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return <FaceScale {...props} />;
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
