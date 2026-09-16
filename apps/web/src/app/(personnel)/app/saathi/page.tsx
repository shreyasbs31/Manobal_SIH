"use client";

import { AudioClearedChip, CaptionStream, VoiceContour, type VoiceState } from "@manobal/ui";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { browserInjectionHit, browserLexiconHit } from "@/lib/lexicon";
import {
  ON_DEVICE_HINDI_NOTE,
  ON_DEVICE_LABEL,
  localReflect,
  onDeviceCapability,
} from "@/lib/on-device";
import { useEngine } from "@/lib/use-engine";

const MODES = ["Check in", "Ask", "Talk it through"] as const;
const MODE_API = {
  "Check in": "checkin",
  Ask: "ask",
  "Talk it through": "reflect",
} as const;
const HOSTING_CAPTION =
  "Prototype: open-weight model hosted on Azure. Deployable on force servers.";
const DEMO_BANNER =
  "Demo mode: speech is processed by a cloud service. In deployment this runs on the phone or your unit's server.";

type CaptionLine = { speaker: "you" | "saathi"; text: string };

export default function SaathiCompanionPage() {
  const { data, error, loading, offline } = useEngine("voice", (client, signal) =>
    client.meVoice(signal),
  );
  const [mode, setMode] = useState<(typeof MODES)[number]>("Check in");
  const [state, setState] = useState<VoiceState>("idle");
  const [amplitude, setAmplitude] = useState(0.08);
  const [lines, setLines] = useState<CaptionLine[]>([]);
  const [clearedMs, setClearedMs] = useState<number | null>(null);
  const [typed, setTyped] = useState("");
  const [keyboard, setKeyboard] = useState(false);
  const [onDevice, setOnDevice] = useState(false);
  const [holding, setHolding] = useState(false);
  const [handsFree, setHandsFree] = useState(false);
  const [hostingCaption, setHostingCaption] = useState(HOSTING_CAPTION);
  const socketRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const playbackRef = useRef<AudioBufferSourceNode | null>(null);
  const silenceRef = useRef(0);

  useEffect(() => {
    void onDeviceCapability().then((result) => setOnDevice(result.available));
  }, []);

  useEffect(() => {
    if (data?.lines.length) {
      setLines(data.lines);
    }
    if (data?.model_caption) {
      setHostingCaption(data.model_caption);
    }
  }, [data]);

  const lang = data?.language === "Tamil" ? "ta" : data?.language === "English" ? "en" : "hi";
  const hinglish = data?.language === "Hinglish";
  const sessionLang = hinglish ? "hi-Latn" : lang;

  const stopPlayback = () => {
    playbackRef.current?.stop();
    playbackRef.current = null;
  };

  const connect = useCallback(() => {
    const token = sessionStorage.getItem("manobal.access_token");
    if (!token) {
      return null;
    }
    const base = process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000";
    const wsUrl = base.replace(/^http/, "ws") + `/api/v1/voice/session?access_token=${token}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data as string) as {
        type: string;
        speaker?: "you" | "saathi";
        text?: string;
        elapsed_ms?: number;
        first_audio_ms?: number;
        audio_b64?: string;
        script?: string;
        hosting_caption?: string;
        interim?: boolean;
      };
      if (payload.hosting_caption) {
        setHostingCaption(payload.hosting_caption);
      }
      if (payload.type === "caption" && payload.text && payload.speaker) {
        const speaker = payload.speaker;
        const text = payload.text;
        if (payload.interim) {
          setLines((current) => {
            const next = [...current];
            const last = next[next.length - 1];
            if (last?.speaker === "you") {
              next[next.length - 1] = { speaker, text };
              return next;
            }
            return [...next, { speaker, text }];
          });
        } else {
          setLines((current) => [...current, { speaker, text }]);
        }
      }
      if (payload.type === "tts") {
        setState("speaking");
        if (payload.audio_b64) {
          const bytes = Uint8Array.from(atob(payload.audio_b64), (char) => char.charCodeAt(0));
          const ctx = ctxRef.current;
          if (ctx) {
            void ctx.decodeAudioData(bytes.buffer.slice(0)).then((buffer) => {
              stopPlayback();
              const source = ctx.createBufferSource();
              const analyser = ctx.createAnalyser();
              source.buffer = buffer;
              source.connect(analyser);
              analyser.connect(ctx.destination);
              playbackRef.current = source;
              source.start();
              const dataArray = new Uint8Array(analyser.fftSize);
              const tick = () => {
                analyser.getByteTimeDomainData(dataArray);
                let sum = 0;
                for (const value of dataArray) {
                  const centred = (value - 128) / 128;
                  sum += centred * centred;
                }
                setAmplitude(Math.min(1, Math.sqrt(sum / dataArray.length) * 4));
              };
              const id = window.setInterval(tick, 80);
              source.onended = () => {
                window.clearInterval(id);
                setState("idle");
                setAmplitude(0.08);
              };
            });
          }
        }
      }
      if (payload.type === "audio.cleared") {
        setClearedMs(payload.elapsed_ms ?? 0);
        setState("idle");
      }
      if (payload.type === "tts.cancelled") {
        stopPlayback();
        setState("listening");
      }
      if (payload.type === "acute") {
        setState("crisis");
        window.location.href = "/app/safety";
      }
    };
    socket.onopen = () => {
      socket.send(JSON.stringify({ type: "start", lang: sessionLang, mode: MODE_API[mode] }));
    };
    return socket;
  }, [mode, sessionLang]);

  const startHold = async () => {
    if (state === "speaking") {
      socketRef.current?.send(JSON.stringify({ type: "barge_in" }));
      stopPlayback();
    }
    setHolding(true);
    setState("listening");
    setClearedMs(null);
    const socket = socketRef.current?.readyState === WebSocket.OPEN ? socketRef.current : connect();
    const ctx = ctxRef.current ?? new AudioContext({ sampleRate: 16000 });
    if (ctx.state === "suspended") {
      await ctx.resume();
    }
    ctxRef.current = ctx;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const source = ctx.createMediaStreamSource(stream);
    await ctx.audioWorklet.addModule("/worklets/pcm-capture.js");
    const node = new AudioWorkletNode(ctx, "pcm-capture");
    node.port.onmessage = (event: MessageEvent<{ pcm: ArrayBuffer; rms: number }>) => {
      setAmplitude(Math.min(1, event.data.rms * 6));
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(event.data.pcm);
      }
      if (handsFree) {
        if (event.data.rms > 0.02) {
          silenceRef.current = 0;
          setState("listening");
        } else {
          silenceRef.current += 1;
          if (silenceRef.current > 12 && socket && socket.readyState === WebSocket.OPEN) {
            silenceRef.current = 0;
            setState("thinking");
            socket.send(JSON.stringify({ type: "end_of_turn" }));
          }
        }
      }
    };
    source.connect(node);
  };

  const endHold = () => {
    setHolding(false);
    if (handsFree) {
      return;
    }
    setState("thinking");
    socketRef.current?.send(JSON.stringify({ type: "end_of_turn" }));
  };

  const sendTyped = async () => {
    const text = typed.trim();
    if (!text) {
      return;
    }
    if (browserLexiconHit(text)) {
      const token = JSON.parse(sessionStorage.getItem("manobal.principal") ?? "{}") as {
        subject_token?: string;
      };
      if (token.subject_token) {
        await engineClient().postAcute({
          token: token.subject_token,
          trigger: "crisis_gate",
          lang: sessionLang,
          channel: "app",
        });
      }
      window.location.href = "/app/safety";
      return;
    }
    if (browserInjectionHit(text)) {
      setLines((current) => [
        ...current,
        { speaker: "you", text },
        {
          speaker: "saathi",
          text: "I cannot follow that request. If you want to talk about rest, sleep, or leave, I am here.",
        },
      ]);
      setTyped("");
      return;
    }
    if (offline && onDevice && sessionLang.startsWith("en") && mode === "Talk it through") {
      setLines((current) => [
        ...current,
        { speaker: "you", text },
        { speaker: "saathi", text: localReflect(text, sessionLang) },
      ]);
      setTyped("");
      return;
    }
    if (offline && onDevice && !sessionLang.startsWith("en")) {
      setLines((current) => [
        ...current,
        { speaker: "you", text },
        { speaker: "saathi", text: ON_DEVICE_HINDI_NOTE },
      ]);
      setTyped("");
      return;
    }
    const result = await engineClient().companionTurn({
      text,
      lang: sessionLang,
      mode: MODE_API[mode],
    });
    if (result.acute) {
      window.location.href = "/app/safety";
      return;
    }
    if (result.hosting_caption) {
      setHostingCaption(result.hosting_caption);
    }
    setLines((current) => [
      ...current,
      { speaker: "you", text },
      { speaker: "saathi", text: result.reply ?? result.script ?? "" },
    ]);
    setTyped("");
  };

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-voice-page">
          <div className="mb-voice-head">
            <h1>Saathi</h1>
            <span>{data.language}</span>
            <Link aria-label="Close" className="mb-flow-close" href="/app">
              x
            </Link>
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
          <VoiceContour amplitude={amplitude} seed={data.persona_id} state={state} />
          <CaptionStream language={data.language} lines={lines} />
          {clearedMs !== null ? <AudioClearedChip ms={clearedMs} /> : null}
          <p className="mb-hosting-caption">{hostingCaption}</p>
          <p className="mb-hosting-caption">{DEMO_BANNER}</p>
          {onDevice ? <p>{ON_DEVICE_LABEL}</p> : null}
          {keyboard ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void sendTyped();
              }}
            >
              <label>
                Message
                <input
                  value={typed}
                  onChange={(event) => setTyped(event.target.value)}
                  autoComplete="off"
                />
              </label>
              <button className="mb-primary" type="submit">
                Send
              </button>
            </form>
          ) : (
            <div className="mb-voice-tools">
              <button
                aria-pressed={holding}
                className="mb-primary mb-hold-talk"
                onMouseDown={() => void startHold()}
                onMouseUp={endHold}
                onTouchStart={() => void startHold()}
                onTouchEnd={endHold}
                type="button"
              >
                Hold to talk
              </button>
              <button className="mb-secondary" onClick={() => setKeyboard(true)} type="button">
                Keyboard
              </button>
              <button
                aria-pressed={handsFree}
                className="mb-ghost"
                onClick={() => {
                  setHandsFree((current) => !current);
                  void startHold();
                }}
                type="button"
              >
                Hands-free
              </button>
            </div>
          )}
        </div>
      ) : null}
    </ScreenState>
  );
}
