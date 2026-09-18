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
            </button>
          );
        })}
      </div>
      <div aria-hidden="true" className="mb-emoji-ends">
        <span>Very low</span>
        <span>Very good</span>
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

export type SafetyPlanFields = {
  warning: string;
  coping: string;
  distract: string;
  help: string;
  professional: string;
  environment: string;
};

const PLAN_DEFAULT: SafetyPlanFields = {
  warning: "Sleep dropping, shorter replies",
  coping: "Box breathing, walk the perimeter",
  distract: "Tea with a buddy, a short walk",
  help: "Buddy, partner",
  professional: "Welfare officer, counsellor desk, Tele-MANAS 14416",
  environment: "Keep medicines with someone I trust. Stay with people tonight.",
};

export function SafetyPlanEditor({
  value,
  onChange,
}: {
  value?: SafetyPlanFields | undefined;
  onChange?: ((next: SafetyPlanFields) => void) | undefined;
} = {}) {
  const [internal, setInternal] = useState(PLAN_DEFAULT);
  const plan = value ?? internal;
  function patch(key: keyof SafetyPlanFields, next: string) {
    const updated = { ...plan, [key]: next };
    if (!value) {
      setInternal(updated);
    }
    onChange?.(updated);
  }
  return (
    <form className="mb-card mb-plan-editor">
      <label>
        Warning signs I notice
        <textarea onChange={(event) => patch("warning", event.target.value)} value={plan.warning} />
      </label>
      <label>
        What I can do on my own
        <textarea onChange={(event) => patch("coping", event.target.value)} value={plan.coping} />
      </label>
      <label>
        People and places that help me shift attention
        <textarea onChange={(event) => patch("distract", event.target.value)} value={plan.distract} />
      </label>
      <label>
        People I can ask for help
        <textarea onChange={(event) => patch("help", event.target.value)} value={plan.help} />
      </label>
      <label>
        Professionals I can contact
        <textarea
          onChange={(event) => patch("professional", event.target.value)}
          value={plan.professional}
        />
      </label>
      <label>
        Making my space safer
        <textarea
          onChange={(event) => patch("environment", event.target.value)}
          value={plan.environment}
        />
      </label>
    </form>
  );
}

export function LeaveWindowPicker({
  start,
  end,
  onChange,
}: {
  start?: string | undefined;
  end?: string | undefined;
  onChange?: ((next: { start: string; end: string }) => void) | undefined;
}) {
  const [innerStart, setInnerStart] = useState("2026-10-04");
  const [innerEnd, setInnerEnd] = useState("2026-10-12");
  const startValue = start ?? innerStart;
  const endValue = end ?? innerEnd;
  return (
    <form className="mb-card mb-leave">
      <label>
        Suggested window start
        <input
          onChange={(event) => {
            const next = { start: event.target.value, end: endValue };
            setInnerStart(next.start);
            onChange?.(next);
          }}
          type="date"
          value={startValue}
        />
      </label>
      <label>
        Suggested window end
        <input
          onChange={(event) => {
            const next = { start: startValue, end: event.target.value };
            setInnerEnd(next.end);
            onChange?.(next);
          }}
          type="date"
          value={endValue}
        />
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
