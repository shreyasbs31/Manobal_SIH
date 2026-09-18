"use client";

import { t } from "@manobal/i18n";
import { ContourTexture } from "@manobal/ui";
import Link from "next/link";
import { useEffect, useLayoutEffect, useState } from "react";

import { engineClient, subjectToken } from "@/lib/engine";
import { drainQueue, enqueue, planStore } from "@/lib/offline";
import { announceWorld } from "@/lib/world";

export default function SafetyPage() {
  const [muted, setMuted] = useState(false);
  const [status, setStatus] = useState("Trying to reach your unit");
  const [lang, setLang] = useState("en");
  const hasPlan = typeof window !== "undefined" ? Boolean(planStore()) : false;
  const sms = "sms:+910000000000?body=SOS%20from%20Saathi";

  useLayoutEffect(() => {
    const page = document.querySelector(".mb-safety") as HTMLElement | null;
    const fit = () => {
      if (!page) {
        return;
      }
      page.style.minHeight = `${window.innerHeight}px`;
    };
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem("manobal.language") ?? "en";
    setLang(stored);
    const audio = new Audio(`/audio/safety.${stored === "hi" ? "hi" : stored === "ta" ? "ta" : "en"}.wav`);
    audio.volume = 0.35;
    if (!muted) {
      void audio.play().catch(() => undefined);
    }
    const retry = window.setInterval(() => {
      if (!navigator.onLine || window.localStorage.getItem("manobal.airplane") === "1") {
        setStatus("Trying to reach your unit");
        return;
      }
      void drainQueue(async (kind, payload, id) => {
        await engineClient().syncQueue([
          { kind, payload: payload as Record<string, unknown>, client_id: id },
        ]);
      }, ["acute"]).then((count) => {
        if (count > 0) {
          announceWorld("acute");
          setStatus("A person is being asked to reach you.");
        }
      });
    }, 10_000);
    return () => {
      audio.pause();
      window.clearInterval(retry);
    };
  }, [muted]);

  return (
    <main className="mb-safety">
      <div className="mb-safety-inner">
        <ContourTexture height={640} opacity={0.2} seed="MB-6604" width={390} />
        <h1>{t("safety.title", lang === "hi" || lang === "ta" ? lang : "en")}</h1>
        <p>{t("safety.reaching", lang === "hi" || lang === "ta" ? lang : "en")}</p>
        <div aria-hidden="true" className="mb-breath-ring" />
        <p>Breathe in with the ring</p>
        <a className="mb-btn mb-call-btn" href="tel:14416">
          Call Tele-MANAS 14416
        </a>
        <button
          aria-pressed="true"
          className="mb-btn mb-outline-btn"
          onClick={() => {
            const token = subjectToken();
            const body = {
              token: token ?? "st_unknown",
              trigger: "sos_call_me",
              lang: "hi-Latn",
              channel: "app",
            };
            if (typeof navigator !== "undefined" && !navigator.onLine) {
              void enqueue("acute", body);
              setStatus("Trying to reach your unit");
              return;
            }
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
                announceWorld("acute");
                setStatus(`A person is being asked to reach you. Case ${result.case_id}.`);
              })
              .catch(() => {
                void enqueue("acute", body);
                setStatus("Trying to reach your unit");
              });
          }}
          type="button"
        >
          Ask my welfare officer to call me
        </button>
        <a className="mb-btn mb-outline-btn mb-sms-btn" href={sms}>
          Send SOS by SMS
        </a>
        <Link className="mb-ghost" href="/app/plan">
          {hasPlan ? "Open my safety plan" : "Make a safety plan"}
        </Link>
        <p>{status}</p>
        <button className="mb-ghost" onClick={() => setMuted((value) => !value)} type="button">
          {muted ? "Unmute audio" : "Mute audio"}
        </button>
      </div>
    </main>
  );
}
