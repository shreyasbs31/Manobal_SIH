"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { enqueue } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";

export default function AssessmentItemPage() {
  const params = useParams<{ id: string }>();
  const id = typeof params.id === "string" ? params.id : "pss10";
  const router = useRouter();
  const { data, error, loading, offline } = useEngine(`assessment-${id}`, (client, signal) =>
    client.meAssessment(id, signal),
  );
  const [step, setStep] = useState(0);
  const [conversational, setConversational] = useState(false);

  async function answer(value: number) {
    const item = step + 1;
    if (id === "phq9" && item === 9 && value > 0) {
      if (offline || !navigator.onLine) {
        await enqueue("assessment", { id, item, value, safety: true });
      } else {
        await engineClient().saveAssessment(id, { item, value, conversational });
      }
      router.push("/app/safety");
      return;
    }
    if (offline || !navigator.onLine) {
      await enqueue("assessment", { id, item, value });
    } else {
      const result = await engineClient().saveAssessment(id, {
        item,
        value,
        conversational,
      });
      if (result.safety) {
        router.push("/app/safety");
        return;
      }
    }
    if (data && item >= data.prompts.length) {
      router.push("/app/assessments");
      return;
    }
    setStep((current) => current + 1);
  }

  const prompt = data?.prompts[step];

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data && prompt ? (
        <div className="mb-checkin">
          <p>
            {step + 1} of {data.prompts.length}
          </p>
          {data.self_only ? <p className="mb-self-only">Self-only. Stays on this phone.</p> : null}
          <h1>{conversational ? `Saathi: ${prompt}` : prompt}</h1>
          <audio controls preload="auto" src="/audio/grounding.en.wav">
            Read aloud
          </audio>
          <div className="mb-option-stack">
            {data.options.map((option, index) => (
              <button className="mb-secondary" key={option} onClick={() => void answer(index)} type="button">
                {option}
              </button>
            ))}
          </div>
          <button className="mb-ghost" onClick={() => setConversational(true)} type="button">
            Conversational mode
          </button>
          {step > 0 ? (
            <button className="mb-ghost" onClick={() => setStep((current) => current - 1)} type="button">
              Back
            </button>
          ) : null}
        </div>
      ) : null}
    </ScreenState>
  );
}
