"use client";

import { BaselineRibbonChart, FaceScale } from "@manobal/ui";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useFlowMeta } from "@/lib/flow-meta";
import { enqueue } from "@/lib/offline";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";
import { announceWorld } from "@/lib/world";

const TAGS = [
  "Duty",
  "Family",
  "Health",
  "Money",
  "Colleagues",
  "Leave",
  "Land or property",
  "Nothing specific",
] as const;

export default function CheckInPage() {
  const { lang, p } = usePersonnelI18n();
  const { data, error, loading, offline } = useEngine("check-in", async (client, signal) => {
    const [home, checkin] = await Promise.all([client.meHome(signal), client.meCheckIn(signal)]);
    return { home, checkin };
  });
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<number[]>([0, 0, 0]);
  const [hours, setHours] = useState(6);
  const [tags, setTags] = useState<string[]>([]);
  const [more, setMore] = useState(false);
  const [savedLine, setSavedLine] = useState<string | null>(null);
  const questions = data?.checkin.questions ?? [];
  const busy = Boolean(data?.checkin.busy_day) && !more;
  const visible = busy ? questions.slice(0, 1) : questions;
  const question = visible[step];
  const tagStep = !busy && questions.length > 0 && step === questions.length;
  const hoursStep = !busy && step === questions.length + 1;
  const done = Boolean(savedLine);
  const questionCount = Math.max(visible.length, 1);
  useFlowMeta(
    done || !question ? undefined : p("{step} of {total}", { step: step + 1, total: questionCount }),
  );

  useEffect(() => {
    const onBack = (event: Event) => {
      if (done || step <= 0) {
        return;
      }
      event.preventDefault();
      setStep((current) => current - 1);
    };
    window.addEventListener("manobal-screen-back", onBack);
    return () => window.removeEventListener("manobal-screen-back", onBack);
  }, [done, step]);

  const joined = useMemo(
    () => [
      ...(data?.home.ribbon ?? []),
      { day: 15, value: answers[0] ? 3.5 + answers[0] * 0.4 : 4.2 },
    ],
    [answers, data],
  );

  async function finish() {
    const body = {
      mood: answers[0] || 3,
      energy: busy ? undefined : answers[1] || 3,
      sleep_quality: busy ? undefined : answers[2] || 3,
      sleep_hours: busy ? undefined : hours,
      tags,
      channel: "tap",
    };
    const line = p("Saved. Thank you for checking in.");
    const airplane =
      typeof window !== "undefined" && window.localStorage.getItem("manobal.airplane") === "1";
    const networkDown =
      offline || airplane || (typeof navigator !== "undefined" && !navigator.onLine);
    if (networkDown) {
      await enqueue("checkin", body);
      setSavedLine(line);
      return;
    }
    try {
      await engineClient().saveCheckIn(body);
      announceWorld("checkin");
      setSavedLine(line);
    } catch {
      await enqueue("checkin", body);
      setSavedLine(line);
    }
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data && !offline}>
      {done ? (
        <div className="mb-checkin">
          <BaselineRibbonChart
            copy={{
              usualRange: p("Your usual range"),
              dataTable: p("Data table"),
              day: p("Day"),
              value: p("Value"),
              outsideRange: p("is outside the usual range"),
            }}
            label={p("Your rhythm")}
            takeaway={savedLine ?? p("Saved. Thank you for checking in.")}
            values={joined}
            variant="hero"
          />
          <Link className="mb-primary" href="/app">
            {p("Done")}
          </Link>
        </div>
      ) : question ? (
        <div className="mb-checkin">
          <h1>{p(question.prompt)}</h1>
          <FaceScale
            label={p(question.id === "mood" ? "Mood" : question.id === "energy" ? "Energy" : "Sleep")}
            levelLabels={[
              p("Very low"),
              p("Low"),
              p("Okay"),
              p("Good"),
              p("Very good"),
            ]}
            onChange={(value) => {
              const next = [...answers];
              next[step] = value;
              setAnswers(next);
              window.setTimeout(() => setStep((current) => current + 1), 180);
            }}
            value={answers[step] ?? 0}
          />
          {busy ? (
            <button className="mb-ghost" onClick={() => setMore(true)} type="button">
              {p("More")}
            </button>
          ) : null}
          <div className="mb-progress-line" aria-hidden="true">
            <span style={{ width: `${((step + 1) / Math.max(visible.length, 1)) * 100}%` }} />
          </div>
          <Link className="mb-secondary" href="/app/saathi">
            {p("Say it instead")}
          </Link>
          {offline ? (
            <div>
              <p>{p("Listen, then tap an answer.")}</p>
              <audio controls preload="auto" src={`/audio/grounding.${lang === "hi" ? "hi" : "en"}.wav`} />
            </div>
          ) : null}
        </div>
      ) : tagStep ? (
        <div className="mb-checkin">
          <h1>{p("Anything on your mind?")}</h1>
          <div className="mb-tag-row">
            {TAGS.map((tag) => (
              <button
                aria-pressed={tags.includes(tag)}
                className="mb-ghost"
                key={tag}
                onClick={() => {
                  setTags((current) =>
                    current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
                  );
                }}
                type="button"
              >
                {p(tag)}
              </button>
            ))}
          </div>
          <button className="mb-primary" onClick={() => setStep((current) => current + 1)} type="button">
            {p("Continue")}
          </button>
        </div>
      ) : hoursStep ? (
        <div className="mb-checkin">
          <h1>{p("About how many hours did you sleep?")}</h1>
          <label>
            {p("Sleep hours")}
            <input
              max={12}
              min={0}
              onChange={(event) => setHours(Number(event.target.value))}
              step={0.5}
              type="number"
              value={hours}
            />
          </label>
          <button className="mb-primary" onClick={() => void finish()} type="button">
            {p("Save")}
          </button>
        </div>
      ) : (busy || offline) && !question ? (
        <div className="mb-checkin">
          <h1>{p("Save this check-in")}</h1>
          <button className="mb-primary" onClick={() => void finish()} type="button">
            {p("Save")}
          </button>
        </div>
      ) : null}
    </ScreenState>
  );
}
