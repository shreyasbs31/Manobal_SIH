"use client";

import { SafetyPlanEditor, type SafetyPlanFields } from "@manobal/ui";
import { useState } from "react";

import { planStore, savePlan } from "@/lib/offline";

export default function SafetyPlanPage() {
  const stored = typeof window !== "undefined" ? planStore() : null;
  const [plan, setPlan] = useState<SafetyPlanFields>({
    warning: stored?.warning ?? "Sleep dropping, shorter replies",
    coping: stored?.coping ?? "Box breathing, walk the perimeter",
    distract: stored?.distract ?? "Tea with a buddy, a short walk",
    help: stored?.help ?? "Buddy, partner",
    professional: stored?.professional ?? "Welfare officer, counsellor desk, Tele-MANAS 14416",
    environment: stored?.environment ?? "Keep medicines with someone I trust.",
  });
  const [saved, setSaved] = useState(false);

  return (
    <div className="mb-home-stack">
      <p>Stored on this phone. Officers never see this.</p>
      <SafetyPlanEditor onChange={setPlan} value={plan} />
      <button
        className="mb-primary"
        onClick={() => {
          savePlan(plan);
          setSaved(true);
        }}
        type="button"
      >
        Save on this phone
      </button>
      {saved ? <p>Saved on this phone.</p> : null}
    </div>
  );
}
