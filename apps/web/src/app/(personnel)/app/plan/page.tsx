"use client";

import { SafetyPlanEditor, type SafetyPlanFields } from "@manobal/ui";
import { useState } from "react";

import { planStore, savePlan } from "@/lib/offline";
import { usePersonnelI18n } from "@/lib/personnel-i18n";

export default function SafetyPlanPage() {
  const { p } = usePersonnelI18n();
  const stored = typeof window !== "undefined" ? planStore() : null;
  const [plan, setPlan] = useState<SafetyPlanFields>({
    warning: stored?.warning ?? p("Sleep dropping, shorter replies"),
    coping: stored?.coping ?? p("Box breathing, walk the perimeter"),
    distract: stored?.distract ?? p("Tea with a buddy, a short walk"),
    help: stored?.help ?? p("Buddy, partner"),
    professional: stored?.professional ?? p("Welfare officer, counsellor desk, Tele-MANAS 14416"),
    environment: stored?.environment ?? p("Keep medicines with someone I trust."),
  });
  const [saved, setSaved] = useState(false);

  return (
    <div className="mb-home-stack">
      <p>{p("Stored on this phone. Officers never see this.")}</p>
      <SafetyPlanEditor
        copy={{
          warning: p("Warning signs I notice"),
          coping: p("What I can do on my own"),
          distract: p("People and places that help me shift attention"),
          help: p("People I can ask for help"),
          professional: p("Professionals I can contact"),
          environment: p("Making my space safer"),
        }}
        onChange={setPlan}
        value={plan}
      />
      <button
        className="mb-primary"
        onClick={() => {
          savePlan(plan);
          setSaved(true);
        }}
        type="button"
      >
        {p("Save on this phone")}
      </button>
      {saved ? <p>{p("Saved on this phone.")}</p> : null}
    </div>
  );
}
