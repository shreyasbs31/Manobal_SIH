"use client";

import { breathPulse, useBreath, usePrefersReducedMotion } from "@manobal/ui";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { engineClient } from "@/lib/engine";
import { browserLexiconHit } from "@/lib/lexicon";

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
  anger_cooldown: { title: "Anger cool-down", body: "Walk the perimeter once. Count steps. Speak later." },
  letter_home: { title: "Letter home", body: "Write to someone who matters. It stays on this phone unless you send it." },
  journal: { title: "Private journal", body: "This stays on this phone." },
  music_decompress: { title: "Music after duty", audio: "/audio/breathing.en.wav", body: "A quiet listen to come down." },
  articles: { title: "Short reads", body: "Sleep on rotating shifts, napping, and talking to family." },
};

export default function ToolkitItemPage() {
  const params = useParams<{ id: string }>();
  const id = typeof params.id === "string" ? params.id : "grounding";
  const item = COPY[id] ?? { title: "Toolkit", body: "A short rest practice." };
  const breath = useBreath(true);
  const reduced = usePrefersReducedMotion();
  const inhale = breath >= 0.5;
  const [count, setCount] = useState(4);
  const last = useRef(inhale);
  const breathing = id === "box_breathing" || id === "four_seven_eight";

  useEffect(() => {
    if (id === "box_breathing") {
      window.location.replace("/app/toolkit/breathe");
    }
  }, [id]);

  useEffect(() => {
    if (last.current === inhale) {
      return;
    }
    last.current = inhale;
    setCount(4);
    breathPulse();
  }, [inhale]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCount((value) => (value <= 1 ? 4 : value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [inhale]);

  const scale = reduced ? 1 : 0.86 + breath * 0.24;

  return (
    <main className={breathing ? "mb-breathe" : "mb-home-stack"} style={{ padding: breathing ? undefined : 16 }}>
      <Link className="mb-ghost mb-breathe-exit" href="/app/toolkit">
        Close
      </Link>
      {breathing ? (
        <div className="mb-breathe-inner">
          <div className="mb-breath-ring" style={{ transform: `scale(${scale})` }} />
          <p className="mb-breathe-count">{count}</p>
          <p>{inhale ? "Breathe in" : "Breathe out"}</p>
        </div>
      ) : (
        <>
          <h1 className="mb-type-title">{item.title}</h1>
          <p>{item.body}</p>
          {item.audio ? <audio controls preload="auto" src={item.audio} /> : null}
          {id === "journal" ? (
            <JournalBox />
          ) : (
            <button
              className="mb-primary"
              onClick={() => {
                void engineClient().request(`/api/v1/me/toolkit/${id}/reward?reward=helped`, {
                  method: "POST",
                });
              }}
              type="button"
            >
              This helped
            </button>
          )}
          <button
            className="mb-ghost"
            onClick={() => {
              void engineClient().request(`/api/v1/me/toolkit/${id}/reward?reward=not_for_me`, {
                method: "POST",
              });
            }}
            type="button"
          >
            Not for me
          </button>
        </>
      )}
    </main>
  );
}

function JournalBox() {
  const [text, setText] = useState("");
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (browserLexiconHit(text)) {
          window.location.href = "/app/safety";
          return;
        }
        const raw = window.localStorage.getItem("manobal.journal");
        const items = raw ? (JSON.parse(raw) as { at: string; text: string }[]) : [];
        items.push({ at: new Date().toISOString(), text });
        window.localStorage.setItem("manobal.journal", JSON.stringify(items));
        setText("");
      }}
    >
      <label>
        Private journal
        <textarea onChange={(event) => setText(event.target.value)} value={text} />
      </label>
      <button className="mb-primary" type="submit">
        Save on this phone
      </button>
    </form>
  );
}
