import type { Page } from "@playwright/test";

const ENGINE = process.env.ENGINE_URL ?? "http://localhost:8000";

export async function signIn(
  page: Page,
  role: string,
  personaId?: string,
): Promise<void> {
  const response = await page.request.post(`${ENGINE}/api/v1/auth/demo-login`, {
    data: {
      role,
      persona_id: personaId ?? null,
    },
  });
  const login = (await response.json()) as {
    access_token: string;
    principal: unknown;
  };
  await page.goto("/login");
  await page.evaluate((payload) => {
    sessionStorage.setItem("manobal.access_token", payload.access_token);
    sessionStorage.setItem("manobal.principal", JSON.stringify(payload.principal));
  }, login);
}

export function roleForRoute(route: string): { role: string; persona?: string } | null {
  if (route.startsWith("/app")) {
    return { role: "personnel", persona: "arjun" };
  }
  if (route.startsWith("/welfare")) {
    return { role: "uwo" };
  }
  if (route.startsWith("/counsel")) {
    return { role: "counsellor" };
  }
  if (route.startsWith("/medical")) {
    return { role: "mo" };
  }
  if (route.startsWith("/hq")) {
    return { role: "hq" };
  }
  if (route.startsWith("/command")) {
    return { role: "commander" };
  }
  if (route.startsWith("/governance") || route.startsWith("/lab")) {
    return { role: "wdec" };
  }
  if (route.startsWith("/dpo")) {
    return { role: "dpo" };
  }
  if (route.startsWith("/integrations")) {
    return { role: "hrms_integrator" };
  }
  if (route.startsWith("/admin")) {
    return { role: "admin" };
  }
  if (route.startsWith("/director")) {
    return { role: "director" };
  }
  return null;
}
