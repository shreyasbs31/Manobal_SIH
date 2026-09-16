"use client";

import {
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser";
import type {
  AuthenticationResponseJSON,
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  RegistrationResponseJSON,
} from "@simplewebauthn/types";
import type { LoginResponse } from "@manobal/contracts";

const engineUrl =
  process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000";

interface OptionsEnvelope<T> {
  transaction_id: string;
  options: T;
}

async function post<TResponse>(
  path: string,
  body: object,
): Promise<TResponse> {
  const response = await fetch(`${engineUrl}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    throw new Error("The passkey request could not be completed");
  }
  return payload as TResponse;
}

export async function registerPasskey(
  personaId: string,
): Promise<LoginResponse> {
  const envelope = await post<
    OptionsEnvelope<PublicKeyCredentialCreationOptionsJSON>
  >(
    "/api/v1/auth/passkey/register/options",
    { persona_id: personaId },
  );
  const credential: RegistrationResponseJSON = await startRegistration({
    optionsJSON: envelope.options,
  });
  return post<LoginResponse>(
    "/api/v1/auth/passkey/register/verify",
    {
      transaction_id: envelope.transaction_id,
      credential,
    },
  );
}

export async function loginWithPasskey(
  personaId: string,
): Promise<LoginResponse> {
  const envelope = await post<
    OptionsEnvelope<PublicKeyCredentialRequestOptionsJSON>
  >(
    "/api/v1/auth/passkey/login/options",
    { persona_id: personaId },
  );
  const credential: AuthenticationResponseJSON = await startAuthentication({
    optionsJSON: envelope.options,
  });
  return post<LoginResponse>(
    "/api/v1/auth/passkey/login/verify",
    {
      transaction_id: envelope.transaction_id,
      credential,
    },
  );
}
