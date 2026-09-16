"use client";

import { arjunVoice } from "@manobal/contracts";
import { AudioClearedChip, CaptionStream, VoiceContour } from "@manobal/ui";
import { useEffect, useState } from "react";

const MODES = ["Check in", "Ask", "Talk it through"] as const;

export default function SaathiCompanionPage() {
  const [mode, setMode] = useState<(typeof MODES)[number]>("Talk it through");
  const [amplitude, setAmplitude] = useState(0.35);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setAmplitude(0.22 + Math.abs(Math.sin(Date.now() / 520)) * 0.55);
    }, 80);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="mb-voice-page">
      <div className="mb-voice-head">
        <h1>Saathi</h1>
        <span>{arjunVoice.language}</span>
      </div>
      <div className="mb-segment" role="group" aria-label="Conversation mode">
        {MODES.map((item) => (
          <button
            aria-pressed={item === mode}
            className="mb-ghost"
            key={item}
            onClick={() => setMode(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </div>
      <VoiceContour amplitude={amplitude} seed={arjunVoice.persona_id} state="listening" />
      <CaptionStream language="" lines={arjunVoice.lines} />
      <AudioClearedChip />
      <p>{arjunVoice.model_caption}. Audio cleared in {arjunVoice.audio_cleared_ms} ms.</p>
      <div className="mb-voice-tools">
        <button className="mb-primary mb-hold-talk" type="button">
          Hold to talk
        </button>
        <button className="mb-secondary" type="button">
          Keyboard
        </button>
      </div>
    </div>
  );
}
