const DB_NAME = "manobal-saathi";
const STORE = "queue";
const SNAP = "snap";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(SNAP)) {
        db.createObjectStore(SNAP);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function asBuffer(bytes: Uint8Array): ArrayBuffer {
  const copy = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(copy).set(bytes);
  return copy;
}

async function cryptoKey(): Promise<CryptoKey> {
  const raw = window.localStorage.getItem("manobal.queue-key");
  let bytes: Uint8Array;
  if (raw) {
    bytes = Uint8Array.from(atob(raw), (char) => char.charCodeAt(0));
  } else {
    bytes = crypto.getRandomValues(new Uint8Array(32));
    window.localStorage.setItem("manobal.queue-key", btoa(String.fromCharCode(...bytes)));
  }
  return crypto.subtle.importKey("raw", asBuffer(bytes), "AES-GCM", false, ["encrypt", "decrypt"]);
}

async function encrypt(payload: unknown): Promise<{ iv: number[]; data: number[] }> {
  const key = await cryptoKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(JSON.stringify(payload));
  const buffer = await crypto.subtle.encrypt({ name: "AES-GCM", iv: asBuffer(iv) }, key, asBuffer(encoded));
  return { iv: [...iv], data: [...new Uint8Array(buffer)] };
}

async function decrypt(record: { iv: number[]; data: number[] }): Promise<unknown> {
  const key = await cryptoKey();
  const buffer = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: asBuffer(new Uint8Array(record.iv)) },
    key,
    asBuffer(new Uint8Array(record.data)),
  );
  return JSON.parse(new TextDecoder().decode(buffer)) as unknown;
}

export async function enqueue(kind: string, payload: unknown): Promise<string> {
  const db = await openDb();
  const id = `${kind}-${crypto.randomUUID()}`;
  const sealed = await encrypt(payload);
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put({ id, kind, ...sealed, at: Date.now() });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  window.dispatchEvent(new Event("manobal-queue"));
  return id;
}

export async function queueCount(): Promise<number> {
  if (typeof indexedDB === "undefined") {
    return 0;
  }
  try {
    const db = await openDb();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const request = tx.objectStore(STORE).count();
      request.onsuccess = () => resolve(Number(request.result));
      request.onerror = () => reject(request.error);
    });
  } catch {
    return 0;
  }
}

export async function drainQueue(
  send: (kind: string, payload: unknown, id: string) => Promise<void>,
  kinds?: readonly string[],
): Promise<number> {
  const db = await openDb();
  const rows = await new Promise<{ id: string; kind: string; iv: number[]; data: number[] }[]>(
    (resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const request = tx.objectStore(STORE).getAll();
      request.onsuccess = () => resolve(request.result as { id: string; kind: string; iv: number[]; data: number[] }[]);
      request.onerror = () => reject(request.error);
    },
  );
  let drained = 0;
  for (const row of rows) {
    if (kinds && !kinds.includes(row.kind)) {
      continue;
    }
    const payload = await decrypt(row);
    await send(row.kind, payload, row.id);
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(row.id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    drained += 1;
    window.dispatchEvent(new Event("manobal-queue"));
  }
  return drained;
}

export async function saveSnapshot(key: string, value: unknown): Promise<void> {
  const db = await openDb();
  const sealed = await encrypt(value);
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(SNAP, "readwrite");
    tx.objectStore(SNAP).put(sealed, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function loadSnapshot<T>(key: string): Promise<T | null> {
  try {
    const db = await openDb();
    const record = await new Promise<{ iv: number[]; data: number[] } | undefined>((resolve, reject) => {
      const tx = db.transaction(SNAP, "readonly");
      const request = tx.objectStore(SNAP).get(key);
      request.onsuccess = () => resolve(request.result as { iv: number[]; data: number[] } | undefined);
      request.onerror = () => reject(request.error);
    });
    if (!record) {
      return null;
    }
    return (await decrypt(record)) as T;
  } catch {
    return null;
  }
}

export function localNudgeRules(input: {
  sleepNightsLow?: number;
  consecutiveDuty?: number;
}): { title: string; why: string }[] {
  const cards = [];
  if ((input.sleepNightsLow ?? 0) >= 3) {
    cards.push({
      title: "Sleep toolkit",
      why: "Three nights of low sleep on this phone.",
    });
  }
  if ((input.consecutiveDuty ?? 0) >= 10) {
    cards.push({
      title: "Five-minute recovery",
      why: "Ten duty days in a row in the cached roster.",
    });
  }
  return cards;
}

export function planStore() {
  const raw = window.localStorage.getItem("manobal.safety-plan");
  return raw ? (JSON.parse(raw) as Record<string, string>) : null;
}

export function savePlan(plan: Record<string, string>) {
  window.localStorage.setItem("manobal.safety-plan", JSON.stringify(plan));
}

export function journalStore() {
  const raw = window.localStorage.getItem("manobal.journal");
  return raw ? (JSON.parse(raw) as { at: string; text: string }[]) : [];
}

export function saveJournal(text: string) {
  const items = journalStore();
  items.push({ at: new Date().toISOString(), text });
  window.localStorage.setItem("manobal.journal", JSON.stringify(items));
}
