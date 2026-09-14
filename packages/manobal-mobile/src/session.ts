export type MobileSession = {
  token: string;
  subjectToken: string;
  unitCode: string;
};

export type SecretStore = {
  get: (key: string) => Promise<string | null>;
  set: (key: string, value: string) => Promise<void>;
  clear: (key: string) => Promise<void>;
};

const SESSION_KEY = "manobal.session";

export function memoryStore(initial: Record<string, string> = {}): SecretStore {
  const rows = { ...initial };
  return {
    get: async (key) => rows[key] ?? null,
    set: async (key, value) => {
      rows[key] = value;
    },
    clear: async (key) => {
      delete rows[key];
    },
  };
}

export async function readSession(store: SecretStore): Promise<MobileSession | null> {
  const raw = await store.get(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<MobileSession>;
    if (parsed.token && parsed.subjectToken && parsed.unitCode) {
      return {
        token: parsed.token,
        subjectToken: parsed.subjectToken,
        unitCode: parsed.unitCode,
      };
    }
  } catch {
    return null;
  }
  return null;
}

export async function writeSession(store: SecretStore, session: MobileSession): Promise<void> {
  await store.set(SESSION_KEY, JSON.stringify(session));
}

export async function clearSession(store: SecretStore): Promise<void> {
  await store.clear(SESSION_KEY);
}
