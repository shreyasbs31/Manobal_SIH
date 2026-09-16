"use client";

import { languages } from "@manobal/i18n";
import { SceneOnboardingPhone } from "@manobal/illustrations";
import {
  ConsentToggleCard,
  LanguageGrid,
  ReceiptCard,
} from "@manobal/ui";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { engineClient } from "@/lib/engine";

const PROMISE = [
  {
    title: "Support, not surveillance",
    body: "This app is here to help you rest, talk, and reach a person. It is not a watch on your unit.",
  },
  {
    title: "Your commander never sees you",
    body: "Command sees only unit patterns. Your name and your check-ins stay out of that view.",
  },
  {
    title: "You control your data",
    body: "You can pause, erase, or download what is stored. Change any choice later in Me.",
  },
] as const;

const HELPERS = [
  "music",
  "prayer or reflection",
  "walking",
  "sport",
  "talking to someone",
  "breathing",
  "writing",
  "sleep",
] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [language, setLanguage] = useState("hi");
  const [consents, setConsents] = useState<Record<string, boolean>>({
    hr_derived: true,
    self_report: false,
    wearable: false,
    ai_conversation: false,
    voice: false,
  });
  const [understood, setUnderstood] = useState(false);
  const [simpleMode, setSimpleMode] = useState(true);
  const [helpers, setHelpers] = useState<string[]>(["music", "talking to someone"]);
  const [family, setFamily] = useState("partner_and_child");
  const [receipt, setReceipt] = useState<{ hash: string; time: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [skipBuddy, setSkipBuddy] = useState(true);
  const [skipPlan, setSkipPlan] = useState(true);
  const [skipWearable, setSkipWearable] = useState(true);
  const tier = useMemo(() => {
              const memory =
                typeof navigator !== "undefined"
                  ? (navigator as Navigator & { deviceMemory?: number }).deviceMemory
                  : undefined;
    return memory && memory >= 4 ? "A" : "B";
  }, []);

  const consentCards = [
    {
      id: "hr_derived",
      title: "Duty and leave from records",
      leavesPhone: "Duty hours and leave balances, already on unit systems",
      whoCanSee: "Welfare officer for your unit, never your commander by name",
    },
    {
      id: "self_report",
      title: "Daily check-in",
      leavesPhone: "Mood, energy, sleep, and tags you choose",
      whoCanSee: "Only you unless you ask someone to help",
    },
    {
      id: "wearable",
      title: "Wearable rest signals",
      leavesPhone: "Rest and heart-rate summaries, not a live stream",
      whoCanSee: "Only you, and a welfare officer if you later share a trend",
    },
    {
      id: "ai_conversation",
      title: "Talks with Saathi",
      leavesPhone: "A short session summary. Audio is cleared.",
      whoCanSee: "Only you",
    },
    {
      id: "voice",
      title: "Voice on this phone",
      leavesPhone: "Speech is turned into text, then the audio is dropped",
      whoCanSee: "Only you",
    },
  ] as const;

  async function finish() {
    setError(null);
    try {
      const result = await engineClient().completeOnboarding({
        language,
        consents,
        exception_understood: understood,
        simple_mode: simpleMode,
        helpers,
        family_context: family,
        skip_buddy: skipBuddy,
        skip_safety_plan: skipPlan,
        skip_wearable: skipWearable,
        device_tier: tier,
      });
      setReceipt(result.receipt);
      window.localStorage.setItem("manobal.onboarding_done", "1");
      window.localStorage.setItem("manobal.language", language);
      window.localStorage.setItem("manobal.simple_mode", simpleMode ? "1" : "0");
      setStep(8);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save");
    }
  }

  return (
    <div className="mb-home-stack mb-onboard">
      {step === 0 ? (
        <>
          <h1 className="mb-type-title">Choose your language</h1>
          <p>Audio greetings play when speech is available on this phone.</p>
          <LanguageGrid
            languages={languages.map((item) => ({
              tag: item.tag,
              label: item.label,
              direction: item.direction,
            }))}
            onChange={setLanguage}
            value={language}
          />
          <button className="mb-primary" onClick={() => setStep(1)} type="button">
            Continue
          </button>
        </>
      ) : null}

      {step === 1 ? (
        <>
          <h1 className="mb-type-title">Before we start</h1>
          <p>Demo sign-in is already done. OTP for this demo is 000000. You can add a passkey later.</p>
          {PROMISE.map((card) => (
            <article className="mb-context-card" key={card.title}>
              <SceneOnboardingPhone />
              <div>
                <h2>{card.title}</h2>
                <p>{card.body}</p>
              </div>
            </article>
          ))}
          <button className="mb-primary" onClick={() => setStep(2)} type="button">
            Continue
          </button>
        </>
      ) : null}

      {step === 2 ? (
        <>
          <h1 className="mb-type-title">What you share</h1>
          <p>Duty records start on. Everything else starts off. Change anytime.</p>
          {consentCards.map((card) => (
            <ConsentToggleCard
              checked={consents[card.id] ?? false}
              key={card.id}
              leavesPhone={card.leavesPhone}
              onChange={(next) => {
                if (card.id === "hr_derived") {
                  return;
                }
                setConsents((current) => ({ ...current, [card.id]: next }));
              }}
              title={card.title}
              whoCanSee={card.whoCanSee}
            />
          ))}
          <button className="mb-primary" onClick={() => setStep(3)} type="button">
            Continue
          </button>
        </>
      ) : null}

      {step === 3 ? (
        <>
          <h1 className="mb-type-title">The one exception</h1>
          <article className="mb-context-card">
            <SceneOnboardingPhone />
            <div>
              <p>
                If you are in immediate danger, a welfare officer and a medical officer are asked
                to reach you. That is the one exception. Your commander still does not see your
                check-ins or talks with Saathi.
              </p>
            </div>
          </article>
          <button
            aria-pressed={understood}
            className={understood ? "mb-primary" : "mb-secondary"}
            onClick={() => setUnderstood(true)}
            type="button"
          >
            I understand
          </button>
          <button
            className="mb-primary"
            disabled={!understood}
            onClick={() => setStep(4)}
            type="button"
          >
            Continue
          </button>
        </>
      ) : null}

      {step === 4 ? (
        <>
          <h1 className="mb-type-title">Optional extras</h1>
          <p>All of these can wait. Skipping still takes you to Home.</p>
          <label className="mb-check-row">
            <input
              checked={!skipBuddy}
              onChange={(event) => setSkipBuddy(!event.target.checked)}
              type="checkbox"
            />
            Set up a buddy now
          </label>
          <label className="mb-check-row">
            <input
              checked={!skipPlan}
              onChange={(event) => setSkipPlan(!event.target.checked)}
              type="checkbox"
            />
            Write a safety plan now
          </label>
          <label className="mb-check-row">
            <input
              checked={!skipWearable}
              onChange={(event) => setSkipWearable(!event.target.checked)}
              type="checkbox"
            />
            Connect a wearable now
          </label>
          <button className="mb-primary" onClick={() => setStep(5)} type="button">
            Continue
          </button>
          <button className="mb-ghost" onClick={() => setStep(5)} type="button">
            Skip extras
          </button>
        </>
      ) : null}

      {step === 5 ? (
        <>
          <h1 className="mb-type-title">This phone</h1>
          <article className="mb-context-card">
            <SceneOnboardingPhone />
            <div>
              <h2>Tier {tier}</h2>
              <p>
                {tier === "A"
                  ? "This phone can keep richer audio cached."
                  : "This phone uses smaller audio and a simpler layout so it stays quick."}
              </p>
            </div>
          </article>
          <button className="mb-primary" onClick={() => setStep(6)} type="button">
            Continue
          </button>
        </>
      ) : null}

      {step === 6 ? (
        <>
          <h1 className="mb-type-title">How you like to use apps</h1>
          <button
            aria-pressed={simpleMode}
            className={simpleMode ? "mb-primary" : "mb-secondary"}
            onClick={() => setSimpleMode(true)}
            type="button"
          >
            Fewer words, larger buttons
          </button>
          <button
            aria-pressed={!simpleMode}
            className={!simpleMode ? "mb-primary" : "mb-secondary"}
            onClick={() => setSimpleMode(false)}
            type="button"
          >
            Show more detail
          </button>
          <h2 className="mb-section-label">What helps me</h2>
          <div className="mb-chip-row">
            {HELPERS.map((helper) => (
              <button
                aria-pressed={helpers.includes(helper)}
                className="mb-ghost"
                key={helper}
                onClick={() => {
                  setHelpers((current) =>
                    current.includes(helper)
                      ? current.filter((item) => item !== helper)
                      : [...current, helper],
                  );
                }}
                type="button"
              >
                {helper}
              </button>
            ))}
          </div>
          <label>
            Family context, optional
            <select onChange={(event) => setFamily(event.target.value)} value={family}>
              <option value="">Skip</option>
              <option value="partner_and_child">Partner and child</option>
              <option value="children_with_grandparents">Children with grandparents</option>
              <option value="bereavement_return">Returning after a loss</option>
            </select>
          </label>
          {error ? <p role="alert">{error}</p> : null}
          <button className="mb-primary" onClick={() => void finish()} type="button">
            Save and show receipt
          </button>
        </>
      ) : null}

      {step === 8 && receipt ? (
        <>
          <h1 className="mb-type-title">Your consent receipt</h1>
          <ReceiptCard hash={receipt.hash} time={receipt.time} />
          <p>Skipped extras do not block Home. You can set them up later in Me.</p>
          <button className="mb-primary" onClick={() => router.push("/app")} type="button">
            Go to Home
          </button>
        </>
      ) : null}
    </div>
  );
}
