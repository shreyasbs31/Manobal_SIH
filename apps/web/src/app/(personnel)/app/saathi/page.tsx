"use client";

import { AudioClearedChip, CaptionStream, VoiceContour, type VoiceState } from "@manobal/ui";
import { useCallback, useEffect, useRef, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import {
  currentAccessToken,
  engineClient,
  inStageFrame,
  refreshDemoSession,
  subjectToken,
  voiceWebSocketUrl,
} from "@/lib/engine";
import { browserInjectionHit, browserLexiconHit } from "@/lib/lexicon";
import { enqueue, saveJournal } from "@/lib/offline";
import { announceWorld } from "@/lib/world";
import {
  ON_DEVICE_HINDI_NOTE,
  ON_DEVICE_LABEL,
  localReflect,
  onDeviceCapability,
} from "@/lib/on-device";
import { useEngine } from "@/lib/use-engine";

const COMPANION_MODE = "checkin";
const HOSTING_CAPTION =
  "Prototype: open-weight model hosted on Azure. Deployable on force servers.";
const DEMO_BANNER =
  "Demo mode: speech is processed by a cloud service. In deployment this runs on the phone or your unit's server.";
const HOLD_HINT = "Press and hold while you speak. Release to send.";
const MIN_HOLD_MS = 500;
const MIN_PEAK_RMS = 0.06;

type CaptionLine = { speaker: "you" | "saathi"; text: string };

function upsertCaption(
  current: CaptionLine[],
  speaker: "you" | "saathi",
  text: string,
  interim = false,
): CaptionLine[] {
  const last = current[current.length - 1];
  if (interim && last?.speaker === speaker) {
    return [...current.slice(0, -1), { speaker, text }];
  }
  if (!interim && speaker === "saathi" && last?.speaker === "saathi") {
    const merged = `${last.text} ${text}`.replace(/\s+/g, " ").trim();
    return [...current.slice(0, -1), { speaker, text: merged }];
  }
  if (!interim && last?.speaker === speaker && last.text === text) {
    return current;
  }
  return [...current, { speaker, text }];
}

export default function SaathiCompanionPage() {
  const { data, error, loading, offline } = useEngine("voice", (client, signal) =>
    client.meVoice(signal),
  );
  const [state, setState] = useState<VoiceState>("idle");
  const [amplitude, setAmplitude] = useState(0.08);
  const [lines, setLines] = useState<CaptionLine[]>([]);
  const [clearedMs, setClearedMs] = useState<number | null>(null);
  const [typed, setTyped] = useState("");
  const [keyboard, setKeyboard] = useState(false);
  const [onDevice, setOnDevice] = useState(false);
  const [holding, setHolding] = useState(false);
  const [sending, setSending] = useState(false);
  const [hostingCaption, setHostingCaption] = useState(HOSTING_CAPTION);
  const [summary, setSummary] = useState("");
  const [fixtureBusy, setFixtureBusy] = useState(false);
  const [journalSaved, setJournalSaved] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(HOLD_HINT);

  const fixtureId =
    typeof window === "undefined"
      ? null
      : new URLSearchParams(window.location.search).get("fixture");
  const socketRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const playbackRef = useRef<AudioBufferSourceNode | null>(null);
  const holdGen = useRef(0);
  const holdActive = useRef(false);
  const captureArmed = useRef(false);
  const holdStartedAt = useRef(0);
  const peakRms = useRef(0);
  const micStreamRef = useRef<MediaStream | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const workletRef = useRef<AudioWorkletNode | null>(null);
  const silentRef = useRef<GainNode | null>(null);
  const sessionReadyRef = useRef(false);
  const readyWaiters = useRef<Array<() => void>>([]);
  const sendingRef = useRef(false);
  const workletLoaded = useRef(false);
  const authRetry = useRef(false);
  const ttsQueue = useRef<AudioBuffer[]>([]);
  const ttsPlaying = useRef(false);
  const ttsPending = useRef(0);
  const ttsClosed = useRef(true);
  const ttsGen = useRef(0);
  const ttsChain = useRef(Promise.resolve());

  useEffect(() => {
    void onDeviceCapability().then((result) => setOnDevice(result.available));
  }, []);

  useEffect(() => {
    if (data?.model_caption) {
      setHostingCaption(data.model_caption);
    }
  }, [data]);

  const lang = data?.language === "Tamil" ? "ta" : data?.language === "English" ? "en" : "hi";
  const hinglish = data?.language === "Hinglish";
  const sessionLang = hinglish ? "hi-Latn" : lang;

  const stopPlayback = () => {
    ttsGen.current += 1;
    ttsQueue.current = [];
    ttsPlaying.current = false;
    ttsPending.current = 0;
    ttsClosed.current = true;
    try {
      playbackRef.current?.stop();
    } catch {
      // Already stopped.
    }
    playbackRef.current = null;
  };

  const settleIfQuiet = () => {
    if (holdActive.current) {
      return;
    }
    if (ttsPlaying.current || ttsQueue.current.length > 0 || ttsPending.current > 0) {
      return;
    }
    if (!ttsClosed.current) {
      return;
    }
    setState("idle");
    setAmplitude(0.08);
  };

  const playNextClip = () => {
    if (ttsPlaying.current) {
      return;
    }
    const ctx = ctxRef.current;
    const buffer = ttsQueue.current.shift();
    if (!ctx || !buffer) {
      ttsPlaying.current = false;
      settleIfQuiet();
      return;
    }
    ttsPlaying.current = true;
    setState("speaking");
    if (ctx.state === "suspended") {
      void ctx.resume();
    }
    const source = ctx.createBufferSource();
    const analyser = ctx.createAnalyser();
    source.buffer = buffer;
    source.connect(analyser);
    analyser.connect(ctx.destination);
    playbackRef.current = source;
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
    const gen = ttsGen.current;
    source.onended = () => {
      window.clearInterval(id);
      if (gen !== ttsGen.current) {
        return;
      }
      ttsPlaying.current = false;
      playbackRef.current = null;
      playNextClip();
    };
    source.start();
  };

  const enqueueTts = (bytes: Uint8Array) => {
    const AudioCtx =
      window.AudioContext ||
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    const ctx = ctxRef.current ?? new AudioCtx();
    ctxRef.current = ctx;
    const gen = ttsGen.current;
    ttsClosed.current = false;
    ttsPending.current += 1;
    setState("speaking");
    ttsChain.current = ttsChain.current
      .then(async () => {
        if (gen !== ttsGen.current) {
          return;
        }
        if (ctx.state === "suspended") {
          await ctx.resume();
        }
        const copy = new ArrayBuffer(bytes.byteLength);
        new Uint8Array(copy).set(bytes);
        const buffer = await ctx.decodeAudioData(copy);
        if (gen !== ttsGen.current) {
          return;
        }
        ttsQueue.current.push(buffer);
        playNextClip();
      })
      .catch(() => {
        // Drop a bad clip and keep the rest of the reply.
      })
      .finally(() => {
        if (gen !== ttsGen.current) {
          return;
        }
        ttsPending.current = Math.max(0, ttsPending.current - 1);
        playNextClip();
      });
  };

  const releaseMic = () => {
    workletRef.current?.disconnect();
    sourceRef.current?.disconnect();
    silentRef.current?.disconnect();
    workletRef.current = null;
    sourceRef.current = null;
    silentRef.current = null;
    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    micStreamRef.current = null;
    captureArmed.current = false;
  };

  const connect = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState < 2) {
      return socketRef.current;
    }
    const socket = new WebSocket(voiceWebSocketUrl());
    socketRef.current = socket;
    sessionReadyRef.current = false;
    socket.onerror = () => {
      setVoiceNote("Voice could not connect. Sign in again if this keeps happening.");
    };
    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
        sessionReadyRef.current = false;
      }
    };
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
        hint?: string;
      };
      if (payload.type === "auth.failed") {
        void (async () => {
          if (inStageFrame() || authRetry.current) {
            setVoiceNote("Your session ended. Sign in again.");
            if (!inStageFrame()) {
              window.location.assign("/login");
            }
            return;
          }
          authRetry.current = true;
          const ok = await refreshDemoSession();
          if (!ok) {
            setVoiceNote("Your session ended. Sign in again.");
            window.location.assign("/login");
            return;
          }
          socket.close();
          socketRef.current = null;
          connect();
        })();
        return;
      }
      if (payload.type === "session.ready") {
        sessionReadyRef.current = true;
        authRetry.current = false;
        const waiters = readyWaiters.current.splice(0);
        waiters.forEach((resolve) => resolve());
      }
      if (payload.hosting_caption) {
        setHostingCaption(payload.hosting_caption);
      }
      if (payload.type === "no_speech") {
        setState("idle");
        setAmplitude(0.08);
        setVoiceNote("Nothing was heard. Hold the button the whole time you speak, then release.");
        return;
      }
      if (payload.type === "caption" && payload.text && payload.speaker) {
        const speaker = payload.speaker;
        const text = payload.text;
        setLines((current) => upsertCaption(current, speaker, text, Boolean(payload.interim)));
        if (speaker === "you" && !payload.interim) {
          setVoiceNote("Sent. Saathi is writing.");
        }
      }
      if (payload.type === "tts") {
        setVoiceNote(null);
        if (payload.audio_b64) {
          const bytes = Uint8Array.from(atob(payload.audio_b64), (char) => char.charCodeAt(0));
          enqueueTts(bytes);
        }
      }
      if (payload.type === "audio.cleared") {
        setClearedMs(payload.elapsed_ms ?? 0);
        ttsClosed.current = true;
        settleIfQuiet();
      }
      if (payload.type === "tts.cancelled") {
        stopPlayback();
        setState("listening");
      }
      if (payload.type === "acute") {
        setState("crisis");
        announceWorld("acute");
        window.location.href = "/app/safety";
      }
    };
    socket.onopen = () => {
      const access = currentAccessToken() || "";
      socket.send(
        JSON.stringify({
          type: "start",
          lang: sessionLang,
          mode: COMPANION_MODE,
          access_token: access,
        }),
      );
    };
    return socket;
  }, [sessionLang]);

  useEffect(() => {
    return () => {
      holdGen.current += 1;
      holdActive.current = false;
      releaseMic();
      stopPlayback();
      socketRef.current?.close();
      socketRef.current = null;
      void ctxRef.current?.close();
      ctxRef.current = null;
    };
    // Unmount only. releaseMic/stopPlayback are stable closures over refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const waitOpen = async (socket: WebSocket | null, ms = 4000): Promise<WebSocket | null> => {
    if (!socket) {
      return null;
    }
    if (socket.readyState === WebSocket.OPEN) {
      return socket;
    }
    await new Promise<void>((resolve) => {
      socket.addEventListener("open", () => resolve(), { once: true });
      socket.addEventListener("error", () => resolve(), { once: true });
      window.setTimeout(() => resolve(), ms);
    });
    return socket.readyState === WebSocket.OPEN ? socket : null;
  };

  const waitSessionReady = async (ms = 4000): Promise<boolean> => {
    if (sessionReadyRef.current) {
      return true;
    }
    return new Promise((resolve) => {
      const timer = window.setTimeout(() => resolve(sessionReadyRef.current), ms);
      readyWaiters.current.push(() => {
        window.clearTimeout(timer);
        resolve(true);
      });
    });
  };

  const startHold = async (event?: React.PointerEvent<HTMLButtonElement>) => {
    if (event) {
      event.preventDefault();
      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch {
        // Pointer capture is best-effort on older browsers.
      }
    }
    if (holdActive.current || sendingRef.current || fixtureBusy) {
      return;
    }
    holdActive.current = true;
    const gen = holdGen.current + 1;
    holdGen.current = gen;
    captureArmed.current = false;
    peakRms.current = 0;
    holdStartedAt.current = performance.now();
    setVoiceNote("Listening. Keep holding.");
    if (playbackRef.current) {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: "barge_in" }));
      }
      stopPlayback();
    }
    setHolding(true);
    setState("listening");
    setClearedMs(null);
    try {
      const socket = await waitOpen(
        socketRef.current?.readyState === WebSocket.OPEN ? socketRef.current : connect(),
      );
      const ready = await waitSessionReady(4000);
      if (holdGen.current !== gen) {
        return;
      }
      if (!socket || !ready) {
        holdActive.current = false;
        setHolding(false);
        setState("idle");
        setVoiceNote("Could not reach the voice service. Sign in again if this keeps happening.");
        return;
      }
      const AudioCtx =
        window.AudioContext ||
        (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      const ctx = ctxRef.current ?? new AudioCtx();
      if (ctx.state === "suspended") {
        await ctx.resume();
      }
      ctxRef.current = ctx;
      if (!workletLoaded.current) {
        try {
          await ctx.audioWorklet.addModule("/worklets/pcm-capture.js");
        } catch {
          // Processor already registered on this AudioContext.
        }
        workletLoaded.current = true;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      if (holdGen.current !== gen) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      releaseMic();
      micStreamRef.current = stream;
      const source = ctx.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(ctx, "pcm-capture");
      const silent = ctx.createGain();
      silent.gain.value = 0;
      node.port.onmessage = (message: MessageEvent<{ pcm: ArrayBuffer; rms: number }>) => {
        const rms = message.data.rms;
        if (rms > peakRms.current) {
          peakRms.current = rms;
        }
        setAmplitude(Math.min(1, rms * 6));
        if (socket.readyState === WebSocket.OPEN && holdActive.current) {
          socket.send(message.data.pcm);
        }
      };
      source.connect(node);
      node.connect(silent);
      silent.connect(ctx.destination);
      sourceRef.current = source;
      workletRef.current = node;
      silentRef.current = silent;
      captureArmed.current = true;
    } catch {
      if (holdGen.current !== gen) {
        return;
      }
      holdActive.current = false;
      releaseMic();
      setHolding(false);
      setState("idle");
      setVoiceNote("Microphone is blocked. Allow the mic, then hold the button while you speak.");
    }
  };

  const endHold = () => {
    if (!holdActive.current) {
      return;
    }
    holdActive.current = false;
    holdGen.current += 1;
    const heldMs = performance.now() - holdStartedAt.current;
    const heard = captureArmed.current && heldMs >= MIN_HOLD_MS && peakRms.current >= MIN_PEAK_RMS;
    setHolding(false);
    releaseMic();
    if (!heard) {
      setState("idle");
      setAmplitude(0.08);
      if (!captureArmed.current) {
        setVoiceNote(HOLD_HINT);
        return;
      }
      if (heldMs < MIN_HOLD_MS) {
        setVoiceNote(HOLD_HINT);
        return;
      }
      setVoiceNote("Nothing was heard. Hold the button the whole time you speak, then release.");
      return;
    }
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      setState("thinking");
      setVoiceNote("Checking what was heard.");
      socketRef.current.send(JSON.stringify({ type: "end_of_turn", heard: true }));
      return;
    }
    setState("idle");
    setVoiceNote("Voice dropped before that turn could send. Hold to talk again.");
  };

  const playRecorded = async () => {
    if (!fixtureId) {
      return;
    }
    setFixtureBusy(true);
    setState("thinking");
    setVoiceNote("Playing the recorded Director line.");
    try {
      const AudioCtx =
        window.AudioContext ||
        (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      const ctx = ctxRef.current ?? new AudioCtx();
      if (ctx.state === "suspended") {
        await ctx.resume();
      }
      ctxRef.current = ctx;
      const [socket, fixture] = await Promise.all([
        waitOpen(
          socketRef.current?.readyState === WebSocket.OPEN ? socketRef.current : connect(),
          5000,
        ),
        engineClient().voiceFixture(fixtureId),
      ]);
      const ready = await waitSessionReady(5000);
      if (socket && socket.readyState === WebSocket.OPEN && ready) {
        socket.send(JSON.stringify({ type: "transcript_final", text: fixture.transcript }));
      } else {
        setState("idle");
        setVoiceNote("Could not open the voice connection. Sign in again if this keeps happening.");
      }
    } catch (caught: unknown) {
      setState("idle");
      setVoiceNote(caught instanceof Error ? caught.message : "Recorded check-in could not run.");
    } finally {
      setFixtureBusy(false);
    }
  };

  const sendTyped = async () => {
    const text = typed.trim();
    if (!text || sendingRef.current) {
      return;
    }
    sendingRef.current = true;
    setSending(true);
    setTyped("");
    setVoiceNote(null);

    if (browserLexiconHit(text)) {
      const token = subjectToken();
      const payload = {
        token: token ?? "",
        trigger: "crisis_gate",
        lang: sessionLang,
        channel: "app",
      };
      const networkDown =
        offline ||
        !navigator.onLine ||
        window.localStorage.getItem("manobal.airplane") === "1";
      void (async () => {
        try {
          if (networkDown || !payload.token) {
            await enqueue("acute", payload);
            return;
          }
          await engineClient().postAcute(payload);
          announceWorld("acute");
        } catch {
          await enqueue("acute", payload);
        }
      })();
      window.location.href = "/app/safety";
      return;
    }
    if (browserInjectionHit(text)) {
      setLines((current) => [
        ...upsertCaption(current, "you", text),
        {
          speaker: "saathi",
          text: "I cannot follow that request. If you want to talk about rest, sleep, or leave, I am here.",
        },
      ]);
      sendingRef.current = false;
      setSending(false);
      return;
    }
    setLines((current) => upsertCaption(current, "you", text));
    setState("thinking");
    setVoiceNote("Sent. Saathi is writing.");

    if (offline && onDevice && sessionLang.startsWith("en")) {
      setLines((current) => upsertCaption(current, "saathi", localReflect(text, sessionLang)));
      setState("idle");
      setVoiceNote(null);
      sendingRef.current = false;
      setSending(false);
      return;
    }
    if (offline && onDevice && !sessionLang.startsWith("en")) {
      setLines((current) => upsertCaption(current, "saathi", ON_DEVICE_HINDI_NOTE));
      setState("idle");
      setVoiceNote(null);
      sendingRef.current = false;
      setSending(false);
      return;
    }
    if (offline) {
      setLines((current) =>
        upsertCaption(
          current,
          "saathi",
          "Offline. Open this screen once while connected, or wait until the phone is back online.",
        ),
      );
      setState("idle");
      sendingRef.current = false;
      setSending(false);
      return;
    }

    try {
      const AudioCtx =
        window.AudioContext ||
        (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      const ctx = ctxRef.current ?? new AudioCtx();
      if (ctx.state === "suspended") {
        await ctx.resume();
      }
      ctxRef.current = ctx;
      const socket = await waitOpen(
        socketRef.current?.readyState === WebSocket.OPEN ? socketRef.current : connect(),
        5000,
      );
      const ready = await waitSessionReady(5000);
      if (socket && socket.readyState === WebSocket.OPEN && ready) {
        socket.send(JSON.stringify({ type: "transcript_final", text }));
        sendingRef.current = false;
        setSending(false);
        return;
      }
      const result = await engineClient().companionTurn({
        text,
        lang: sessionLang,
        mode: COMPANION_MODE,
      });
      if (result.acute) {
        window.location.href = "/app/safety";
        return;
      }
      if (result.hosting_caption) {
        setHostingCaption(result.hosting_caption);
      }
      const reply = result.reply ?? result.script ?? "";
      if (reply) {
        setLines((current) => upsertCaption(current, "saathi", reply));
        setVoiceNote(null);
      } else {
        setVoiceNote("Saathi could not reply just then. Try again.");
      }
    } catch (caught: unknown) {
      setVoiceNote(caught instanceof Error ? caught.message : "Could not send. Try again.");
    } finally {
      if (sendingRef.current) {
        setState("idle");
        sendingRef.current = false;
        setSending(false);
      }
    }
  };

  const language = data?.language ?? "Hindi";
  const personaId = data?.persona_id ?? "offline";
  const holdBusy = sending || fixtureBusy;

  return (
    <ScreenState error={null} loading={loading && !data && !offline} offline={offline} empty={false}>
      <div className="mb-voice-page">
          <div className="mb-voice-head">
            <h1>Saathi</h1>
            <span>{language}</span>
          </div>
          {error ? <p role="alert">{error}</p> : null}
          {voiceNote ? <p role="status">{voiceNote}</p> : null}
          <VoiceContour amplitude={amplitude} seed={personaId} state={state} />
          {lines.length ? <CaptionStream language={language} lines={lines} /> : null}
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
              <button className="mb-primary" disabled={sending || !typed.trim()} type="submit">
                {sending ? "Sending..." : "Send"}
              </button>
              <button
                className="mb-secondary"
                disabled={sending}
                onClick={() => {
                  setKeyboard(false);
                  setVoiceNote(HOLD_HINT);
                }}
                type="button"
              >
                Back to voice
              </button>
            </form>
          ) : (
            <div className="mb-voice-tools">
              <button
                aria-pressed={holding}
                className="mb-primary mb-hold-talk"
                disabled={holdBusy}
                onContextMenu={(event) => event.preventDefault()}
                onKeyDown={(event) => {
                  if (event.repeat) {
                    return;
                  }
                  if (event.code === "Space" || event.key === " ") {
                    event.preventDefault();
                    void startHold();
                  }
                }}
                onKeyUp={(event) => {
                  if (event.code === "Space" || event.key === " ") {
                    event.preventDefault();
                    endHold();
                  }
                }}
                onPointerCancel={endHold}
                onPointerDown={(event) => {
                  void startHold(event);
                }}
                onPointerUp={endHold}
                type="button"
              >
                {holding ? "Listening" : "Hold to talk"}
              </button>
              <button
                className="mb-secondary"
                onClick={() => {
                  setKeyboard(true);
                  setVoiceNote(null);
                }}
                type="button"
              >
                Keyboard
              </button>
              {fixtureId ? (
                <button
                  className="mb-secondary"
                  disabled={fixtureBusy}
                  onClick={() => void playRecorded()}
                  type="button"
                >
                  Play recorded check-in
                </button>
              ) : null}
            </div>
          )}
          {fixtureId ? (
            <p className="mb-hosting-caption">
              Recorded playback is a Director demo control. It sends a fixed line so a shot can run without a microphone.
            </p>
          ) : null}
          <button
            className="mb-secondary"
            onClick={() => {
              const text = lines.map((line) => `${line.speaker}: ${line.text}`).join(" ");
              setSummary(text.slice(0, 280) || "A short check-in.");
            }}
            type="button"
          >
            End of session summary
          </button>
          {summary ? <p>{summary}</p> : null}
          <button
            className="mb-ghost"
            onClick={() => {
              const text = summary || lines.map((line) => line.text).join(" ");
              if (browserLexiconHit(text)) {
                window.location.href = "/app/safety";
                return;
              }
              saveJournal(text);
              setJournalSaved(true);
            }}
            type="button"
          >
            Save as private journal
          </button>
          {journalSaved ? <p>Saved on this phone. Officers cannot see it.</p> : null}
        </div>
    </ScreenState>
  );
}
