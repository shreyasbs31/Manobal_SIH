"use client";

import {
  ManobalClient,
  type LoginResponse,
  type ManobalRole,
} from "@manobal/contracts";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { engineBaseUrl, persistLogin } from "@/lib/engine";
import { loginWithPasskey, registerPasskey } from "@/lib/passkeys";

const roles: readonly { id: ManobalRole; label: string }[] = [
  { id: "personnel", label: "Personnel" },
  { id: "uwo", label: "Welfare officer" },
  { id: "counsellor", label: "Counsellor" },
  { id: "mo", label: "Medical officer" },
  { id: "commander", label: "Commander" },
  { id: "hq", label: "Force HQ" },
  { id: "wdec", label: "Governance" },
  { id: "dpo", label: "DPO" },
  { id: "hrms_integrator", label: "HRMS integrator" },
  { id: "admin", label: "System admin" },
  { id: "director", label: "Demo director" },
];

const personas = [
  { id: "arjun", label: "Arjun", language: "Hindi" },
  { id: "meena", label: "Meena", language: "Hindi" },
  { id: "imran", label: "Imran", language: "English" },
  { id: "thomas", label: "Thomas", language: "English" },
  { id: "lalit", label: "Lalit", language: "Hindi" },
  { id: "deepak", label: "Deepak", language: "Hinglish" },
  { id: "rajesh", label: "Rajesh", language: "Hindi" },
  { id: "karthik", label: "Karthik", language: "Tamil" },
] as const;

const roleRoutes: Record<ManobalRole, string> = {
  personnel: "/app",
  uwo: "/welfare",
  counsellor: "/counsel",
  mo: "/medical",
  commander: "/command",
  hq: "/hq",
  wdec: "/governance",
  dpo: "/dpo",
  hrms_integrator: "/integrations",
  admin: "/admin",
  director: "/director",
};

const roleIds = new Set<string>(roles.map((role) => role.id));
const operatorRoleIds = new Set<ManobalRole>(["admin", "director"]);

export function DemoLogin({
  gateRequired,
  initialRole,
}: {
  gateRequired: boolean;
  initialRole?: string | undefined;
}) {
  const router = useRouter();
  const requestedRole =
    initialRole && roleIds.has(initialRole)
      ? (initialRole as ManobalRole)
      : "personnel";
  const [role, setRole] = useState<ManobalRole>(
    gateRequired && operatorRoleIds.has(requestedRole)
      ? "personnel"
      : requestedRole,
  );
  const [personaId, setPersonaId] = useState("arjun");
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState("Choose who you are, then continue.");
  const [pin, setPin] = useState("");
  const [operator, setOperator] = useState(!gateRequired);
  const client = useMemo(() => new ManobalClient(engineBaseUrl()), []);
  const availableRoles = useMemo(
    () =>
      operator
        ? roles
        : roles.filter((item) => !operatorRoleIds.has(item.id)),
    [operator],
  );

  useEffect(() => {
    if (!gateRequired) {
      return;
    }
    void fetch("/api/v1/auth/demo-access/status", {
      credentials: "include",
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          return null;
        }
        return (await response.json()) as { access?: string };
      })
      .then((payload) => {
        const hasOperatorAccess = payload?.access === "operator";
        setOperator(hasOperatorAccess);
        if (!hasOperatorAccess && operatorRoleIds.has(role)) {
          setRole("personnel");
        }
      })
      .catch(() => setOperator(false));
  }, [gateRequired, role]);

  function finish(login: LoginResponse) {
    persistLogin(login, {
      role,
      persona_id: role === "personnel" ? personaId : null,
    });
    router.push(roleRoutes[login.principal.role]);
  }

  async function run(action: () => Promise<LoginResponse>) {
    setPending(true);
    setStatus("Signing in.");
    try {
      finish(await action());
    } catch (error: unknown) {
      setStatus(
        error instanceof Error
          ? error.message
          : "The sign-in could not be completed.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mb-home-stack">
      <fieldset className="role-grid">
        <legend>Access as</legend>
        {availableRoles.map((item) => (
          <button
            aria-pressed={role === item.id}
            className="choice-button"
            key={item.id}
            onClick={() => setRole(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </fieldset>

      {role === "personnel" ? (
        <fieldset className="persona-grid">
          <legend>Person</legend>
          {personas.map((persona) => (
            <button
              aria-pressed={personaId === persona.id}
              className="choice-button"
              key={persona.id}
              onClick={() => setPersonaId(persona.id)}
              type="button"
            >
              <strong>{persona.label}</strong>
              <br />
              <small>{persona.language}</small>
            </button>
          ))}
        </fieldset>
      ) : null}

      <div className="mb-action-row">
        <button
          className="mb-primary"
          disabled={pending}
          onClick={() =>
            void run(() =>
              client.demoLogin({
                role,
                persona_id: role === "personnel" ? personaId : null,
              }),
            )
          }
          type="button"
        >
          {pending ? "Signing in" : "Continue"}
        </button>
        {role === "personnel" && !gateRequired ? (
          <>
            <button
              className="mb-secondary"
              disabled={pending}
              onClick={() => void run(() => registerPasskey(personaId))}
              type="button"
            >
              Create passkey
            </button>
            <button
              className="mb-secondary"
              disabled={pending}
              onClick={() => void run(() => loginWithPasskey(personaId))}
              type="button"
            >
              Use passkey
            </button>
            <label>
              Device PIN
              <input
                autoComplete="off"
                inputMode="numeric"
                maxLength={6}
                onChange={(event) => setPin(event.target.value.replace(/\D/g, "").slice(0, 6))}
                value={pin}
              />
            </label>
            <button
              className="mb-secondary"
              disabled={pending || pin.length !== 6}
              onClick={() => {
                const stored = window.localStorage.getItem("manobal.device-pin");
                if (!stored) {
                  window.localStorage.setItem("manobal.device-pin", pin);
                  setStatus("PIN stored on this device only.");
                } else if (stored !== pin) {
                  setStatus("That PIN does not match the one stored on this phone.");
                  return;
                }
                void run(() =>
                  client.demoLogin({
                    role,
                    persona_id: personaId,
                  }),
                );
              }}
              type="button"
            >
              Use device PIN
            </button>
          </>
        ) : null}
      </div>
      <p className="form-status" role="status">
        {status}
      </p>
    </div>
  );
}
