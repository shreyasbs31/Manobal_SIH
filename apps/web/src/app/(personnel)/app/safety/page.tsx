"use client";

import { ContourTexture, useBreath } from "@manobal/ui";
import { useState } from "react";

import { engineClient, subjectToken } from "@/lib/engine";

export default function SafetyPage() {
  const breath = useBreath(true);
  const [muted, setMuted] = useState(false);
  const [status, setStatus] = useState("Reaching your unit ... connected");
  const scale = 0.86 + breath * 0.22;

  return (
    <main className="mb-safety">
      <div className="mb-safety-inner">
        <ContourTexture height={640} opacity={0.2} seed="MB-6604" width={390} />
        <h1>You are not alone.</h1>
        <p>Someone is being asked to reach you.</p>
        <div className="mb-breath-ring" style={{ transform: `scale(${scale})` }} />
        <p>Breathe in with the ring</p>
        <a className="mb-btn mb-call-btn" href="tel:14416">
          Call Tele-MANAS 14416
        </a>
        <button
          aria-pressed="true"
          className="mb-btn mb-outline-btn"
          onClick={() => {
            const token = subjectToken();
            if (!token) {
              setStatus("Sign in as personnel to ask for a call.");
              return;
            }
            void engineClient()
              .postAcute({
                token,
                trigger: "sos_call_me",
                lang: "hi-Latn",
                channel: "app",
              })
              .then((result) => {
                setStatus(`Welfare and medical have been asked. Case ${result.case_id}.`);
              })
              .catch(() => {
                setStatus("Could not reach the acute path. Call Tele-MANAS.");
              });
          }}
          type="button"
        >
          Ask my welfare officer to call me
        </button>
        <button className="mb-btn mb-outline-btn" type="button">
          Send SOS by SMS
        </button>
        <a className="mb-ghost" href="/app/me">
          Open my safety plan
        </a>
        <p>{status}</p>
        <button className="mb-ghost" onClick={() => setMuted((value) => !value)} type="button">
          {muted ? "Unmute audio" : "Mute audio"}
        </button>
      </div>
    </main>
  );
}
