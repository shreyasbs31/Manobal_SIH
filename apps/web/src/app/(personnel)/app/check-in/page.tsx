"use client";

import { BaselineRibbonChart, FaceScale } from "@manobal/ui";
import Link from "next/link";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function CheckInPage() {
  const { data, error, loading, offline } = useEngine("check-in", async (client, signal) => {
    const [home, checkin] = await Promise.all([client.meHome(signal), client.meCheckIn(signal)]);
    return { home, checkin };
  });
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<number[]>([0, 0, 0]);
  const questions = data?.checkin.questions ?? [];
  const question = questions[step];
  const done = questions.length > 0 && step >= questions.length;
  const joined = useMemo(
    () => [
      ...(data?.home.ribbon ?? []),
      { day: 15, value: answers[2] ? 3.5 + answers[2] * 0.4 : 4.2 },
    ],
    [answers, data],
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {done ? (
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
      ) : question ? (
        <div className="mb-checkin">
          <p>
            {step + 1} of {questions.length}
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
            <span style={{ width: `${((step + 1) / questions.length) * 100}%` }} />
          </div>
          <Link className="mb-secondary" href="/app/saathi">
            Say it instead
          </Link>
        </div>
      ) : null}
    </ScreenState>
  );
}
