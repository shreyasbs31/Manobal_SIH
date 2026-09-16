"use client";

import { arjunHome, checkInQuestions } from "@manobal/contracts";
import { BaselineRibbonChart, FaceScale } from "@manobal/ui";
import Link from "next/link";
import { useMemo, useState } from "react";

export default function CheckInPage() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<number[]>([0, 0, 0]);
  const question = checkInQuestions[step];
  const done = step >= checkInQuestions.length;
  const joined = useMemo(
    () => [
      ...arjunHome.ribbon,
      { day: 15, value: answers[2] ? 3.5 + answers[2] * 0.4 : 4.2 },
    ],
    [answers],
  );

  if (done) {
    return (
      <div className="mb-checkin">
        <BaselineRibbonChart
          label="Your rhythm"
          takeaway="Saved. Thank you for checking in."
          values={joined}
          variant="hero"
        />
        <Link className="mb-primary" href="/app">
          Done
        </Link>
      </div>
    );
  }

  if (!question) {
    return null;
  }

  return (
    <div className="mb-checkin">
      <p>
        {step + 1} of {checkInQuestions.length}
      </p>
      <h1>{question.prompt}</h1>
      <FaceScale
        label={question.id === "mood" ? "Mood" : question.id === "energy" ? "Energy" : "Sleep"}
        onChange={(value) => {
          const next = [...answers];
          next[step] = value;
          setAnswers(next);
          window.setTimeout(() => setStep((current) => current + 1), 180);
        }}
        value={answers[step] ?? 0}
      />
      <div className="mb-progress-line" aria-hidden="true">
        <span style={{ width: `${((step + 1) / checkInQuestions.length) * 100}%` }} />
      </div>
      <Link className="mb-secondary" href="/app/saathi">
        Say it instead
      </Link>
    </div>
  );
}
