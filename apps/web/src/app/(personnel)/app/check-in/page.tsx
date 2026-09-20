"use client";

import { t } from "@manobal/i18n";
import { BaselineRibbonChart, FaceScale } from "@manobal/ui";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useFlowMeta } from "@/lib/flow-meta";
import { enqueue } from "@/lib/offline";
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
    done || !question ? undefined : `${step + 1} of ${questionCount}`,
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
    const lang = data?.home.language ?? "en";
    const line = t("checkin.saved", lang === "hi" || lang === "ta" ? lang : "en");
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
      const result = await engineClient().saveCheckIn(body);
      announceWorld("checkin");
      setSavedLine(result.message ?? line);
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
            label="Your rhythm"
            takeaway={savedLine ?? t("checkin.saved", "en")}
            values={joined}
            variant="hero"
          />
          <Link className="mb-primary" href="/app">
            Done
          </Link>
        </div>
      ) : question ? (
        <div className="mb-checkin">
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
          {busy ? (
            <button className="mb-ghost" onClick={() => setMore(true)} type="button">
              More
            </button>
          ) : null}
          <div className="mb-progress-line" aria-hidden="true">
            <span style={{ width: `${((step + 1) / Math.max(visible.length, 1)) * 100}%` }} />
          </div>
          <Link className="mb-secondary" href="/app/saathi">
            Say it instead
          </Link>
          {offline ? (
            <div>
              <p>Listen, then tap an answer.</p>
              <audio controls preload="auto" src="/audio/grounding.en.wav" />
            </div>
          ) : null}
        </div>
      ) : tagStep ? (
        <div className="mb-checkin">
          <h1>Anything on your mind?</h1>
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
                {tag}
              </button>
            ))}
          </div>
          <button className="mb-primary" onClick={() => setStep((current) => current + 1)} type="button">
            Continue
          </button>
        </div>
      ) : hoursStep ? (
        <div className="mb-checkin">
          <h1>About how many hours did you sleep?</h1>
          <label>
            Sleep hours
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
            Save
          </button>
        </div>
      ) : (busy || offline) && !question ? (
        <div className="mb-checkin">
          <h1>Save this check-in</h1>
          <button className="mb-primary" onClick={() => void finish()} type="button">
            Save
          </button>
        </div>
      ) : null}
    </ScreenState>
  );
}
