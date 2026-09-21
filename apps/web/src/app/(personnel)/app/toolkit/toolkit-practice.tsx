"use client";

import { useEffect, useState } from "react";

import { ScreenExit } from "@/components/screen-exit";
import { engineClient } from "@/lib/engine";
import { browserLexiconHit } from "@/lib/lexicon";
import { usePersonnelI18n } from "@/lib/personnel-i18n";

const GROUNDING = [
  { count: 5, prompt: "Name five things you can see." },
  { count: 4, prompt: "Name four things you can feel." },
  { count: 3, prompt: "Name three things you can hear." },
  { count: 2, prompt: "Name two things you can smell." },
  { count: 1, prompt: "Name one thing you can taste." },
];

const NIDRA = [
  "Lie down if you can. Keep the eyes soft. Stay awake.",
  "Feel the weight of the heels, the calves, the back.",
  "Breathe in for four. Let the out-breath be longer.",
  "If a thought arrives, let it pass like a jeep on a far road.",
  "Bring attention back to the room. Wiggle fingers. Sit up slowly.",
];

const SCAN = [
  "Feet and toes",
  "Calves and knees",
  "Thighs and hips",
  "Belly and chest",
  "Hands and arms",
  "Jaw, eyes, forehead",
];

const POST_DUTY = [
  "Sit. Unclench the jaw. Drop the shoulders.",
  "Drink water before tea or a smoke.",
  "Walk the perimeter once without talking.",
  "Tell someone you are off duty, even if it is only a message.",
];

const HEAT = [
  "Sip water before you feel thirsty.",
  "Shade first, then rest. Helmet off in cover if the task allows.",
  "Cool the wrists and neck, not ice on the chest.",
];

const COLD = [
  "Warm the hands before sleep. Dry socks matter more than a second layer on the chest.",
  "Eat something warm if you can. Cold and empty sleep is worse.",
  "Tell a buddy if shivering will not stop.",
];

const ARTICLES = [
  { title: "Sleep on rotating shifts", body: "A short rest after night duty is not laziness. Protect a dark, quiet block even if it is only four hours." },
  { title: "Talking to family from far away", body: "A ten-minute call with one question is enough. You do not have to report the whole week." },
  { title: "After a hard incident", body: "Eat, drink, sleep if you can. Talking can wait until someone you trust is free." },
];

function markHelped(id: string, reward: "helped" | "not_for_me") {
  void engineClient().request(`/api/v1/me/toolkit/${id}/reward?reward=${reward}`, {
    method: "POST",
  });
}

function JournalBox() {
  const { p } = usePersonnelI18n();
  const [text, setText] = useState("");
  const [saved, setSaved] = useState(0);
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
        setSaved(items.length);
      }}
    >
      <label>
        {p("Private journal")}
        <textarea onChange={(event) => setText(event.target.value)} value={text} />
      </label>
      <button className="mb-primary" type="submit">
        {p("Save on this phone")}
      </button>
      <p>{saved ? p("{n} notes on this phone.", { n: saved }) : p("Officers never see this.")}</p>
    </form>
  );
}

function StepPractice({
  steps,
  doneLabel,
}: {
  steps: string[];
  doneLabel: string;
}) {
  const { p } = usePersonnelI18n();
  const [step, setStep] = useState(0);
  const current = steps[step];
  if (!current) {
    return <p>{p(doneLabel)}</p>;
  }
  return (
    <div className="mb-practice">
      <p>
        {p("{step} of {total}", { step: step + 1, total: steps.length })}
      </p>
      <h2>{p(current)}</h2>
      <button className="mb-primary" onClick={() => setStep((value) => value + 1)} type="button">
        {p(step + 1 === steps.length ? "Finish" : "Next")}
      </button>
    </div>
  );
}

function GroundingPractice() {
  const { p } = usePersonnelI18n();
  const [step, setStep] = useState(0);
  const [named, setNamed] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const current = GROUNDING[step];
  if (!current) {
    return <p>{p("You named what is here. Stay with that for one more breath.")}</p>;
  }
  return (
    <form
      className="mb-practice"
      onSubmit={(event) => {
        event.preventDefault();
        const next = draft.trim();
        if (!next) {
          return;
        }
        setNamed((items) => [...items, next]);
        setDraft("");
        if (named.length + 1 >= current.count) {
          setNamed([]);
          setStep((value) => value + 1);
        }
      }}
    >
      <p>
        {p("{n} left in this step", { n: current.count - named.length })}
      </p>
      <h2>{p(current.prompt)}</h2>
      {named.map((item) => (
        <p key={item}>{item}</p>
      ))}
      <label>
        {p("Write one")}
        <input onChange={(event) => setDraft(event.target.value)} value={draft} />
      </label>
      <button className="mb-primary" type="submit">
        {p("Add")}
      </button>
    </form>
  );
}

function TimedPractice({
  seconds,
  label,
  audio,
}: {
  seconds: number;
  label: string;
  audio?: string;
}) {
  const { p } = usePersonnelI18n();
  const [left, setLeft] = useState(seconds);
  const [running, setRunning] = useState(false);
  useEffect(() => {
    if (!running || left <= 0) {
      return;
    }
    const id = window.setTimeout(() => setLeft((value) => value - 1), 1000);
    return () => window.clearTimeout(id);
  }, [left, running]);
  const minutes = Math.floor(left / 60);
  const secs = String(left % 60).padStart(2, "0");
  return (
    <div className="mb-practice">
      <p>{p(label)}</p>
      <p className="mb-breathe-count">{minutes}:{secs}</p>
      {audio ? <audio controls preload="auto" src={audio} /> : null}
      <button
        className="mb-primary"
        onClick={() => {
          setRunning(true);
          if (left === 0) {
            setLeft(seconds);
          }
        }}
        type="button"
      >
        {p(running ? (left === 0 ? "Start again" : "Running") : "Start")}
      </button>
    </div>
  );
}

function Checklist({ items }: { items: string[] }) {
  const { p } = usePersonnelI18n();
  const [done, setDone] = useState<boolean[]>(() => items.map(() => false));
  return (
    <ul className="mb-practice-list">
      {items.map((item, index) => (
        <li key={item}>
          <label className="mb-check-row">
            <input
              checked={done[index] ?? false}
              onChange={() => {
                const next = [...done];
                next[index] = !next[index];
                setDone(next);
              }}
              type="checkbox"
            />
            {p(item)}
          </label>
        </li>
      ))}
    </ul>
  );
}

function LetterHome() {
  const { p } = usePersonnelI18n();
  const [text, setText] = useState(
    typeof window === "undefined" ? "" : window.localStorage.getItem("manobal.letter") ?? "",
  );
  const [saved, setSaved] = useState(false);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (browserLexiconHit(text)) {
          window.location.href = "/app/safety";
          return;
        }
        window.localStorage.setItem("manobal.letter", text);
        setSaved(true);
      }}
    >
      <label>
        {p("Letter home")}
        <textarea onChange={(event) => setText(event.target.value)} rows={8} value={text} />
      </label>
      <p>{p("This stays on this phone unless you copy it out yourself.")}</p>
      <button className="mb-primary" type="submit">
        {p("Save on this phone")}
      </button>
      {saved ? <p>{p("Saved on this phone.")}</p> : null}
    </form>
  );
}

function AngerWalk() {
  const { p } = usePersonnelI18n();
  const [steps, setSteps] = useState(0);
  return (
    <div className="mb-practice">
      <p>{p("Walk the perimeter. Tap once each time you pass the start.")}</p>
      <p className="mb-breathe-count">{steps}</p>
      <button className="mb-primary" onClick={() => setSteps((value) => value + 1)} type="button">
        {p("I passed the start")}
      </button>
      {steps >= 1 ? <p>{p("Speak later. You do not have to settle this now.")}</p> : null}
    </div>
  );
}

export function ToolkitPractice({
  id,
  title,
  body,
  audio,
}: {
  id: string;
  title: string;
  body: string;
  audio?: string | undefined;
}) {
  const { lang, p } = usePersonnelI18n();
  const localAudio = lang === "hi" ? audio?.replace(".en.", ".hi.") : audio;
  return (
    <main className="mb-overlay-page">
      <h1 className="mb-sr-only">{p(title)}</h1>
      <ScreenExit backHref="/app/toolkit" title={p(title)} />
      <p>{p(body)}</p>
      {id === "grounding" ? <GroundingPractice /> : null}
      {id === "sleep_wind_down" ? (
        <TimedPractice
          audio={localAudio ?? `/audio/breathing.${lang === "hi" ? "hi" : "en"}.wav`}
          label="Ten quiet minutes"
          seconds={600}
        />
      ) : null}
      {id === "yoga_nidra" ? (
        <StepPractice doneLabel="Sit up when you are ready." steps={NIDRA} />
      ) : null}
      {id === "body_scan" ? (
        <StepPractice doneLabel="The scan is done. Nothing to fix." steps={SCAN} />
      ) : null}
      {id === "post_duty" ? (
        <StepPractice doneLabel="The shift can end here." steps={POST_DUTY} />
      ) : null}
      {id === "tactical_nap" ? (
        <TimedPractice label="Ten to twenty minutes. Soft alarm." seconds={720} />
      ) : null}
      {id === "heat_cold" ? (
        <>
          <h2 className="mb-section-label">{p("Heat")}</h2>
          <Checklist items={HEAT} />
          <h2 className="mb-section-label">{p("Cold")}</h2>
          <Checklist items={COLD} />
        </>
      ) : null}
      {id === "anger_cooldown" ? <AngerWalk /> : null}
      {id === "letter_home" ? <LetterHome /> : null}
      {id === "journal" ? <JournalBox /> : null}
      {id === "music_decompress" ? (
        <audio controls preload="auto" src={localAudio ?? `/audio/breathing.${lang === "hi" ? "hi" : "en"}.wav`} />
      ) : null}
      {id === "articles" ? (
        <div>
          {ARTICLES.map((article) => (
            <article className="mb-context-card" key={article.title}>
              <div>
                <h2>{p(article.title)}</h2>
                <p>{p(article.body)}</p>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <button
        className="mb-primary"
        onClick={() => {
          markHelped(id, "helped");
          window.localStorage.setItem("manobal.toolkit.last", id);
        }}
        type="button"
      >
        {p("This helped")}
      </button>
      <button
        className="mb-ghost"
        onClick={() => markHelped(id, "not_for_me")}
        type="button"
      >
        {p("Not for me")}
      </button>
    </main>
  );
}
