"use client";

import { PhoneFrame, RibbonMark, SimClock } from "@manobal/ui";
import { ManobalClient, type ManobalRole, type Principal } from "@manobal/contracts";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  engineBaseUrl,
  STAGE_CONSOLE_FRAME,
  STAGE_PHONE_FRAME,
  storeStageSession,
} from "@/lib/engine";
import { allowedConsolePath, allowedPhonePath, roleForPath } from "@/lib/stage-role";

const SHOT_INSTRUCTIONS: Record<string, string> = {
  voice: "Sign in as Arjun. Click Play recorded check-in. Hindi reply, then audio-cleared.",
  karthik: "Sign in as Karthik. Click Play recorded check-in. Tamil reply, then audio-cleared.",
  deepak: "Sign in as Deepak. Click Play recorded check-in. Safety screen. T4 on Welfare and Medical within 5 seconds.",
  "deepak-typed": "Sign in as Deepak. Keyboard. Type main jeena nahi chahta. Send. Safety screen, no model reply.",
  copilot: "Open copilot. Ask who is under strain in Charlie Coy. Refusal, no names.",
  "copilot-aggregate": "Switch console language if needed. Open copilot. Use the night share prompt. Live answer plus chart.",
  "hindi-brief": "Switch the console to Hindi. Open MB-4091. Brief with [tier] [domain] [onset] [lever] marks.",
  "deepgram-outage": "Director: Deepgram outage. Sign in as Meena. Play recorded check-in. Turn still completes.",
  lab: "Read precision, recall, Brier and the source line. Imran T1, Thomas T0.",
  governance: "Read the source line under the KPIs. Figures come from core or demo cases.",
  offline: "Airplane on. Open check-in, toolkit, safety. Save still works. Drain after airplane off.",
};

const SHOT_LABELS: Record<string, string> = {
  landing: "Landing ribbon",
  onboarding: "Hindi onboarding",
  checkin: "Twenty second check-in",
  voice: "Hindi voice check-in",
  drift: "Arjun time travel",
  workspace: "Case workspace reveal",
  "imran-thomas": "Imran and Thomas",
  formation: "Formation and hidden tile",
  copilot: "Copilot refusal",
  "copilot-aggregate": "Copilot aggregate",
  roster: "Roster balancer",
  deepak: "Deepak spoken distress and T4",
  "deepak-typed": "Deepak typed distress",
  "hindi-brief": "Hindi case brief",
  "deepgram-outage": "Deepgram outage fallback",
  governance: "Governance chain",
  lab: "Validation lab",
  offline: "Offline then sync",
  architecture: "Zones and self-test",
  close: "Landing second fold",
  karthik: "Karthik Tamil voice",
  rajesh: "Rajesh grievance",
  lalit: "Lalit incident",
  meena: "Meena leave planner",
};

function pathOnly(value: string): string {
  return value.split("?")[0] ?? value;
}

function safePath(
  value: string | null,
  allowed: (path: string) => boolean,
  fallback: string,
): string {
  if (!value) {
    return fallback;
  }
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("://")) {
    return fallback;
  }
  return allowed(pathOnly(value)) ? value : fallback;
}

const SHOT_PERSONA: Record<string, string> = {
  voice: "arjun",
  karthik: "karthik",
  deepak: "deepak",
  "deepak-typed": "deepak",
  meena: "meena",
  "deepgram-outage": "meena",
  checkin: "arjun",
  onboarding: "arjun",
  workspace: "arjun",
  drift: "arjun",
};

function phonePersona(phonePath: string, shot?: string): string {
  const query = phonePath.split("?")[1] ?? "";
  const fixture = new URLSearchParams(query).get("fixture") ?? "";
  if (fixture.startsWith("karthik")) {
    return "karthik";
  }
  if (fixture.startsWith("deepak")) {
    return "deepak";
  }
  if (fixture.startsWith("meena")) {
    return "meena";
  }
  if (shot && SHOT_PERSONA[shot]) {
    return SHOT_PERSONA[shot];
  }
  return "arjun";
}

function consoleRole(consolePath: string): ManobalRole {
  const needed = roleForPath(pathOnly(consolePath));
  return needed === "any" || needed === "personnel" ? "director" : needed;
}

const ROLE_LABEL: Record<ManobalRole, string> = {
  personnel: "Personnel",
  uwo: "Welfare officer",
  counsellor: "Counsellor",
  mo: "Medical officer",
  commander: "Commander",
  hq: "Force HQ",
  wdec: "Governance",
  dpo: "DPO",
  hrms_integrator: "HRMS integrator",
  admin: "System admin",
  director: "Demo director",
};

const CONSOLE_ROLES: readonly ManobalRole[] = [
  "commander",
  "uwo",
  "counsellor",
  "mo",
  "hq",
  "wdec",
  "dpo",
  "hrms_integrator",
  "admin",
  "director",
];

export function StageView({
  phonePath,
  consolePath,
  shot,
}: {
  phonePath: string;
  consolePath: string;
  shot?: string | undefined;
}) {
  const phone = safePath(phonePath, allowedPhonePath, "/app");
  const consoleSafe = safePath(consolePath, allowedConsolePath, "/command");
  const [drawer, setDrawer] = useState(false);
  const [note, setNote] = useState("");
  const [armed, setArmed] = useState(false);
  const [liveConsole, setLiveConsole] = useState(consoleSafe);
  const [consoleSrc] = useState(consoleSafe);
  const phoneToken = useRef<string | null>(null);
  const consoleToken = useRef<string | null>(null);
  const phonePrincipal = useRef<Principal | null>(null);
  const consolePrincipal = useRef<Principal | null>(null);
  const phoneFrame = useRef<HTMLIFrameElement | null>(null);
  const consoleFrame = useRef<HTMLIFrameElement | null>(null);
  const minting = useRef(false);
  const pendingConsole = useRef<string | null>(null);
  const consoleGen = useRef(0);
  const roleSessions = useRef(new Map<ManobalRole, { token: string; principal: Principal }>());
  const label = (shot && SHOT_LABELS[shot]) || "Home";
  const persona = phonePersona(phone, shot);
  const officerRole = consoleRole(consoleSafe);

  useEffect(() => {
    setLiveConsole(consoleSafe);
  }, [consoleSafe]);

  const postAuth = useCallback(
    (
      target: Window | null | undefined,
      token: string | null,
      principal: Principal | null,
    ) => {
      if (!target || !token) {
        return;
      }
      target.postMessage(
        { type: "manobal.stage.auth", access_token: token, principal },
        window.location.origin,
      );
    },
    [],
  );

  const pushSessions = useCallback(() => {
    postAuth(phoneFrame.current?.contentWindow, phoneToken.current, phonePrincipal.current);
    postAuth(consoleFrame.current?.contentWindow, consoleToken.current, consolePrincipal.current);
  }, [postAuth]);

  const applyConsoleSession = useCallback(
    (token: string, principal: Principal) => {
      consoleToken.current = token;
      consolePrincipal.current = principal;
      storeStageSession(STAGE_CONSOLE_FRAME, token, principal);
      postAuth(consoleFrame.current?.contentWindow, token, principal);
    },
    [postAuth],
  );

  const mintConsole = useCallback(
    async (path: string) => {
      pendingConsole.current = path;
      if (minting.current) {
        return;
      }
      minting.current = true;
      try {
        while (pendingConsole.current) {
          const next = pendingConsole.current;
          pendingConsole.current = null;
          const needed = roleForPath(next);
          if (needed === "any" || needed === "personnel") {
            postAuth(
              consoleFrame.current?.contentWindow,
              consoleToken.current,
              consolePrincipal.current,
            );
            continue;
          }
          const cached = roleSessions.current.get(needed);
          if (cached) {
            applyConsoleSession(cached.token, cached.principal);
            continue;
          }
          if (consolePrincipal.current?.role === needed && consoleToken.current) {
            postAuth(
              consoleFrame.current?.contentWindow,
              consoleToken.current,
              consolePrincipal.current,
            );
            continue;
          }
          const gen = ++consoleGen.current;
          try {
            const login = await new ManobalClient(engineBaseUrl()).demoLogin({
              role: needed,
              persona_id: null,
            });
            if (gen !== consoleGen.current) {
              continue;
            }
            roleSessions.current.set(needed, {
              token: login.access_token,
              principal: login.principal,
            });
            applyConsoleSession(login.access_token, login.principal);
            setArmed(true);
          } catch (caught: unknown) {
            setNote(caught instanceof Error ? caught.message : "Could not prepare the console session.");
          }
        }
      } finally {
        minting.current = false;
        if (pendingConsole.current) {
          void mintConsole(pendingConsole.current);
        }
      }
    },
    [applyConsoleSession, postAuth],
  );

  useEffect(() => {
    if (!armed) {
      return;
    }
    const frame = consoleFrame.current?.contentWindow;
    if (!frame) {
      return;
    }
    let current = "";
    try {
      current = frame.location.pathname;
    } catch {
      current = "";
    }
    if (!current || pathOnly(current) === pathOnly(consoleSafe)) {
      return;
    }
    void mintConsole(consoleSafe).then(() => {
      try {
        frame.location.assign(consoleSafe);
      } catch {
        // Cross-origin during boot is ignored.
      }
    });
  }, [armed, consoleSafe, mintConsole]);

  useEffect(() => {
    let cancelled = false;
    const gen = ++consoleGen.current;
    const client = new ManobalClient(engineBaseUrl());
    void (async () => {
      try {
        const [phoneLogin, consoleLogin] = await Promise.all([
          client.demoLogin({ role: "personnel", persona_id: persona }),
          client.demoLogin({ role: officerRole, persona_id: null }),
        ]);
        if (cancelled || gen !== consoleGen.current) {
          return;
        }
        phoneToken.current = phoneLogin.access_token;
        consoleToken.current = consoleLogin.access_token;
        phonePrincipal.current = phoneLogin.principal;
        consolePrincipal.current = consoleLogin.principal;
        roleSessions.current.set(officerRole, {
          token: consoleLogin.access_token,
          principal: consoleLogin.principal,
        });
        storeStageSession(STAGE_PHONE_FRAME, phoneLogin.access_token, phoneLogin.principal);
        storeStageSession(STAGE_CONSOLE_FRAME, consoleLogin.access_token, consoleLogin.principal);
        setNote("");
        setArmed(true);
        void Promise.allSettled(
          CONSOLE_ROLES.filter((role) => role !== officerRole).map(async (role) => {
            const login = await client.demoLogin({ role, persona_id: null });
            if (cancelled) {
              return;
            }
            roleSessions.current.set(role, {
              token: login.access_token,
              principal: login.principal,
            });
          }),
        );
      } catch (caught: unknown) {
        if (!cancelled) {
          setNote(caught instanceof Error ? caught.message : "Could not prepare stage sessions.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [officerRole, persona]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        return;
      }
      const data = event.data as { type?: string; kind?: string; path?: string; frame?: string };
      if (data?.type === "manobal.stage.console-path" && typeof data.path === "string") {
        const next = safePath(data.path, allowedConsolePath, liveConsole);
        if (next !== liveConsole) {
          setLiveConsole(next);
        }
        return;
      }
      if (data?.type === "manobal.stage.ready") {
        if (event.source === phoneFrame.current?.contentWindow) {
          postAuth(phoneFrame.current?.contentWindow, phoneToken.current, phonePrincipal.current);
        }
        if (event.source === consoleFrame.current?.contentWindow) {
          postAuth(consoleFrame.current?.contentWindow, consoleToken.current, consolePrincipal.current);
        }
        return;
      }
      if (data?.type === "manobal.stage.event") {
        const packet = { type: "manobal.stage.invalidate", kind: data.kind ?? "world" };
        phoneFrame.current?.contentWindow?.postMessage(packet, window.location.origin);
        consoleFrame.current?.contentWindow?.postMessage(packet, window.location.origin);
        return;
      }
      if (
        (data?.type === "manobal.stage.need-role" || data?.type === "manobal.stage.console-go") &&
        typeof data.path === "string"
      ) {
        const next = safePath(data.path, allowedConsolePath, liveConsole);
        if (data.frame === STAGE_PHONE_FRAME) {
          postAuth(phoneFrame.current?.contentWindow, phoneToken.current, phonePrincipal.current);
          return;
        }
        void mintConsole(next).then(() => {
          if (next !== liveConsole) {
            setLiveConsole(next);
          }
        });
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [liveConsole, mintConsole, postAuth]);

  useEffect(() => {
    if (!armed) {
      return;
    }
    pushSessions();
    const id = window.setInterval(pushSessions, 400);
    const stop = window.setTimeout(() => window.clearInterval(id), 8000);
    return () => {
      window.clearInterval(id);
      window.clearTimeout(stop);
    };
  }, [armed, phone, liveConsole, pushSessions]);

  const onKey = useCallback((event: KeyboardEvent) => {
    if (event.key.toLowerCase() === "d" && !event.metaKey && !event.ctrlKey) {
      const target = event.target;
      if (target instanceof HTMLElement && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        return;
      }
      setDrawer((open) => !open);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  return (
    <div className="mb-stage">
      <header className="mb-stage-bar" aria-label="Recording">
        <h1 className="mb-brand">
          <RibbonMark />
          MANOBAL
        </h1>
        <SimClock value="2026-09-16 10:00 IST" />
        <span className="mb-stage-beat">{label}</span>
      </header>
      <main className="mb-stage-split" aria-label="Phone and console">
        <div className="mb-stage-phone">
          <PhoneFrame title="Saathi phone">
            {armed && phoneToken.current ? (
              <iframe
                allow="microphone; autoplay"
                name={STAGE_PHONE_FRAME}
                onLoad={pushSessions}
                ref={phoneFrame}
                src={phone}
                title="Saathi"
                loading="eager"
              />
            ) : (
              <p className="mb-stage-wait" role="status">
                Preparing
              </p>
            )}
          </PhoneFrame>
        </div>
        <div className="mb-stage-console">
          {armed && consoleToken.current ? (
            <iframe
              allow="autoplay"
              name={STAGE_CONSOLE_FRAME}
              onLoad={pushSessions}
              ref={consoleFrame}
              src={consoleSrc}
              title="Command console"
              loading="eager"
            />
          ) : (
            <p className="mb-stage-wait" role="status">
              Preparing
            </p>
          )}
        </div>
      </main>
      <aside className="mb-stage-drawer" data-open={drawer ? "true" : "false"}>
        <p>Director. Press D to hide.</p>
        {note ? <p role="status">{note}</p> : null}
        {shot ? <p>{SHOT_INSTRUCTIONS[shot] ?? label}</p> : null}
        <span>
          Phone session {persona}. Console {ROLE_LABEL[officerRole]}.
        </span>
        <span>{phone}</span>
        <span>{liveConsole}</span>
        <Link className="mb-secondary" href="/director">
          Open director
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=workspace">
          Case reveal
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/saathi&console=/welfare&shot=voice">
          Companion plus queue
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/safety&console=/medical&shot=deepak">
          Safety plus acute
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app&console=/command&shot=formation">
          Formation
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app&console=/governance&shot=governance">
          Governance
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/check-in&console=/architecture&shot=offline">
          Offline
        </Link>
      </aside>
    </div>
  );
}
