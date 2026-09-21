"use client";

import { BreathGuide, FOUR_SEVEN_EIGHT_PATTERN } from "@manobal/ui";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { ScreenExit } from "@/components/screen-exit";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { ToolkitPractice } from "../toolkit-practice";

const COPY: Record<string, { title: string; audio?: string; body: string }> = {
  box_breathing: { title: "Box breathing", body: "A four-count cycle." },
  four_seven_eight: { title: "4-7-8 breathing", body: "In for 4, hold 7, out 8." },
  grounding: {
    title: "5-4-3-2-1 grounding",
    audio: "/audio/grounding.en.wav",
    body: "Name five things you see, four you feel, three you hear, two you smell, one you taste.",
  },
  sleep_wind_down: {
    title: "Sleep wind-down",
    audio: "/audio/breathing.en.wav",
    body: "Ten quiet minutes. Keep the phone face down if you can.",
  },
  yoga_nidra: { title: "Short yoga nidra", body: "Lie down. Stay awake. Follow the rest script." },
  body_scan: { title: "Body scan", body: "Notice each part of the body without judging." },
  post_duty: { title: "Post-duty decompression", body: "Sit. Unclench the jaw. Let the shift end." },
  tactical_nap: { title: "Tactical nap guide", body: "Ten to twenty minutes. Set a soft alarm." },
  heat_cold: { title: "Heat and cold tips", body: "Sip water. Shade first. Warm hands before sleep in the cold." },
  anger_cooldown: { title: "Anger cool-down", body: "Walk the perimeter once. Count laps. Speak later." },
  letter_home: { title: "Letter home", body: "Write to someone who matters. It stays on this phone unless you send it." },
  journal: { title: "Private journal", body: "This stays on this phone." },
  music_decompress: { title: "Music after duty", audio: "/audio/breathing.en.wav", body: "A quiet listen to come down." },
  articles: { title: "Short reads", body: "Sleep on rotating shifts, napping, and talking to family." },
};

export default function ToolkitItemPage() {
  const { p } = usePersonnelI18n();
  const params = useParams<{ id: string }>();
  const id = typeof params.id === "string" ? params.id : "grounding";
  const item = COPY[id] ?? { title: "Toolkit", body: "A short rest practice." };

  useEffect(() => {
    if (id === "box_breathing") {
      window.location.replace("/app/toolkit/breathe");
    }
  }, [id]);

  if (id === "four_seven_eight") {
    return (
      <main className="mb-breathe">
        <h1 className="mb-sr-only">{p("4-7-8 breathing")}</h1>
        <div className="mb-breathe-nav">
          <ScreenExit backHref="/app/toolkit" />
        </div>
        <BreathGuide
          pattern={FOUR_SEVEN_EIGHT_PATTERN}
          title={p("4-7-8 breathing")}
          translateLabel={p}
        />
      </main>
    );
  }

  return <ToolkitPractice audio={item.audio} body={item.body} id={id} title={item.title} />;
}
