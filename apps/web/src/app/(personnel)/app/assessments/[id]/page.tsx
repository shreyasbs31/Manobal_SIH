"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { assessmentTitle } from "@/lib/assessment-titles";
import { engineClient } from "@/lib/engine";
import { useFlowMeta } from "@/lib/flow-meta";
import { enqueue } from "@/lib/offline";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

const OPTIONS = ["Not at all", "Several days", "More than half the days", "Nearly every day"];

const PSS_PROMPTS = [
  "In the last month, how often have you been upset because of something that happened unexpectedly?",
  "In the last month, how often have you felt that you were unable to control the important things in your life?",
  "In the last month, how often have you felt nervous and stressed?",
  "In the last month, how often have you felt confident about your ability to handle your personal problems?",
  "In the last month, how often have you felt that things were going your way?",
  "In the last month, how often have you found that you could not cope with all the things that you had to do?",
  "In the last month, how often have you been able to control irritations in your life?",
  "In the last month, how often have you felt that you were on top of things?",
  "In the last month, how often have you been angered because of things that were outside of your control?",
  "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?",
];

const PHQ9_PROMPTS = [
  "Little interest or pleasure in doing things",
  "Feeling down, low, or hopeless",
  "Trouble falling or staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself",
  "Trouble concentrating",
  "Moving or speaking slowly, or being fidgety",
  "Thoughts that you would be better off dead, or of hurting yourself",
];

const WHO5_PROMPTS = [
  "I have felt cheerful and in good spirits",
  "I have felt calm and relaxed",
  "I have felt active and vigorous",
  "I woke up feeling fresh and rested",
  "My daily life has been filled with things that interest me",
];

const GAD7_PROMPTS = [
  "Feeling nervous, anxious, or on edge",
  "Not being able to stop or control worrying",
  "Worrying too much about different things",
  "Trouble relaxing",
  "Being so restless that it is hard to sit still",
  "Becoming easily annoyed or irritable",
  "Feeling afraid as if something awful might happen",
];

const CBI_PROMPTS = [
  "How often do you feel tired",
  "How often are you physically exhausted",
  "How often are you emotionally exhausted",
  "How often do you think, I cannot take it anymore",
  "How often do you feel worn out",
  "How often do you feel weak and susceptible to illness",
];

const PCPTSD_PROMPTS = [
  "Had nightmares about the event or thought about it when you did not want to",
  "Tried hard not to think about the event or went out of your way to avoid situations that reminded you of it",
  "Been constantly on guard, watchful, or easily startled",
  "Felt numb or detached from people, activities, or your surroundings",
  "Felt guilty or unable to stop blaming yourself or others for the event or any problems it may have caused",
];

const AUDITC_PROMPTS = [
  "How often do you have a drink containing alcohol",
  "How many drinks containing alcohol do you have on a typical day when you are drinking",
  "How often do you have six or more drinks on one occasion",
];

const BUNDLED: Record<
  string,
  { title: string; self_only: boolean; prompts: string[]; options: string[] }
> = {
  pss10: { title: "PSS-10", self_only: false, prompts: PSS_PROMPTS, options: OPTIONS },
  phq9: { title: "PHQ-9", self_only: false, prompts: PHQ9_PROMPTS, options: OPTIONS },
  who5: {
    title: "WHO-5",
    self_only: false,
    prompts: WHO5_PROMPTS,
    options: ["At no time", "Some of the time", "More than half the time", "All of the time"],
  },
  gad7: { title: "GAD-7", self_only: false, prompts: GAD7_PROMPTS, options: OPTIONS },
  cbi: { title: "CBI", self_only: false, prompts: CBI_PROMPTS, options: OPTIONS },
  pcptsd5: { title: "PC-PTSD-5", self_only: false, prompts: PCPTSD_PROMPTS, options: OPTIONS },
  auditc: {
    title: "AUDIT-C",
    self_only: true,
    prompts: AUDITC_PROMPTS,
    options: ["Never", "Monthly or less", "Two to four times a month", "Weekly or more"],
  },
};

function bundledAssessment(id: string) {
  const pack = BUNDLED[id] ?? {
    title: id.toUpperCase(),
    self_only: id === "auditc",
    prompts: Array.from({ length: 5 }, (_, index) => `Item ${index + 1}`),
    options: OPTIONS,
  };
  return { id, items: pack.prompts.length, ...pack };
}

export default function AssessmentItemPage() {
  const { lang, p } = usePersonnelI18n();
  const params = useParams<{ id: string }>();
  const id = typeof params.id === "string" ? params.id : "pss10";
  const router = useRouter();
  const { data, error, loading, offline } = useEngine(`assessment-${id}`, (client, signal) =>
    client.meAssessment(id, signal),
  );
  const view = data ?? bundledAssessment(id);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [conversational, setConversational] = useState(false);
  const [done, setDone] = useState(false);
  useFlowMeta(
    done || !view.prompts.length
      ? undefined
      : p("{step} of {total}", { step: step + 1, total: view.prompts.length }),
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

  async function answer(value: number) {
    const item = step + 1;
    const nextAnswers = [...answers];
    nextAnswers[step] = value;
    setAnswers(nextAnswers);
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
    if (item >= view.prompts.length) {
      setDone(true);
      return;
    }
    setStep((current) => current + 1);
  }

  const prompt = view.prompts[step];

  return (
    <ScreenState error={error && !view ? error : null} loading={loading && !view} offline={offline} empty={false}>
      {done ? (
        <div className="mb-home-stack">
          <h1 className="mb-type-title">{p(assessmentTitle(view.id, view.title))} {p("saved")}</h1>
          <p>
            {view.self_only
              ? p("This stays on this phone. Officers never see it.")
              : p("Saved. You can talk it through if you want.")}
          </p>
          <p>
            {offline
              ? p("You answered {n} questions and they are waiting on this phone.", {
                  n: view.prompts.length,
                })
              : p("You answered {n} questions.", { n: view.prompts.length })}
          </p>
          <Link className="mb-primary" href="/app/saathi">
            {p("Talk with Saathi")}
          </Link>
          <Link className="mb-secondary" href="/app/talk">
            {p("Talk to a person")}
          </Link>
          <Link className="mb-ghost" href="/app/assessments">
            {p("Back to assessments")}
          </Link>
        </div>
      ) : prompt ? (
        <div className="mb-checkin">
          {view.self_only ? <p className="mb-self-only">{p("Stays on this phone.")}</p> : null}
          <h1>{p(prompt)}</h1>
          <audio controls preload="auto" src={`/audio/grounding.${lang === "hi" ? "hi" : "en"}.wav`}>
            {p("Read aloud")}
          </audio>
          <div className="mb-option-stack">
            {view.options.map((option, index) => (
              <button className="mb-secondary" key={option} onClick={() => void answer(index)} type="button">
                {p(option)}
              </button>
            ))}
          </div>
          <button className="mb-ghost" onClick={() => setConversational(true)} type="button">
            {p("Have Saathi ask this")}
          </button>
        </div>
      ) : null}
    </ScreenState>
  );
}
