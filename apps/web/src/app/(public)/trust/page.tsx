"use client";

import { MachineTranslatedBadge, PublicHeader, ValidatedBadge } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { manobalMode } from "@/lib/mode";
import { useEngine } from "@/lib/use-engine";

function pickFemaleVoice(lang: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  const wanted = lang.toLowerCase();
  const ranked = voices.filter((voice) => {
    const blob = `${voice.name} ${voice.lang}`.toLowerCase();
    if (/male|madhur|prabhat|ravi|david|george|valluvar|naveen|ryan|guy|andrew|brian|arthur|tony/.test(blob)) {
      return false;
    }
    return /female|swara|neerja|ananya|heera|pallavi|zira|aria|sonia|neural/.test(blob) || voice.lang.toLowerCase().startsWith(wanted.slice(0, 2));
  });
  return (
    ranked.find((voice) => /swara|neerja|ananya|female/.test(voice.name.toLowerCase())) ??
    ranked.find((voice) => voice.lang.toLowerCase().startsWith(wanted.slice(0, 2))) ??
    ranked[0] ??
    null
  );
}

export default function TrustPage() {
  const [speaking, setSpeaking] = useState(false);
  const { data, error, loading, offline } = useEngine("trust", (client, signal) =>
    client.publicTrust(signal),
  );

  function readAloud() {
    if (!data) {
      return;
    }
    if (typeof window === "undefined" || !window.speechSynthesis) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(data.read_aloud);
    utterance.lang = "en-IN";
    const voice = pickFemaleVoice("en-IN");
    if (voice) {
      utterance.voice = voice;
    }
    utterance.onend = () => setSpeaking(false);
    setSpeaking(true);
    const start = () => window.speechSynthesis.speak(utterance);
    if (window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.addEventListener("voiceschanged", start, { once: true });
      window.setTimeout(start, 250);
      return;
    }
    start();
  }

  return (
    <div className="mb-theme mb-trust" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-trust-main">
        <h1>What MANOBAL collects, and what it never does</h1>
        <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
          {data ? (
            <>
            <p>{data.promise}</p>
            <div className="mb-action-row">
              <button
                aria-pressed={speaking}
                className="mb-primary"
                onClick={readAloud}
                type="button"
              >
                {speaking ? "Reading" : "Read this page aloud"}
              </button>
            </div>
            <table className="mb-compare">
              <caption>What is collected, and what never happens</caption>
              <thead>
                <tr>
                  <th scope="col">Collects</th>
                  <th scope="col">Leaves the phone</th>
                  <th scope="col">Who can see it</th>
                  <th scope="col">The one exception</th>
                </tr>
              </thead>
              <tbody>
                {data.matrix.map((row) => (
                  <tr key={row.collects}>
                    <td>{row.collects}</td>
                    <td>{row.leaves_phone}</td>
                    <td>{row.who}</td>
                    <td>{row.exception}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <h2>Languages</h2>
            <table className="mb-compare">
              <caption>Reviewed and machine-translated languages</caption>
              <thead>
                <tr>
                  <th scope="col">Language</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.languages.map((row) => (
                  <tr key={row.code}>
                    <td>{row.name}</td>
                    <td>{row.reviewed ? <ValidatedBadge /> : <MachineTranslatedBadge />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </>
          ) : null}
        </ScreenState>
      </main>
    </div>
  );
}
