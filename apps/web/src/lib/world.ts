"use client";

const WORLD_CHANNEL = "manobal-world";

let worldChannel: BroadcastChannel | null = null;

function channel(): BroadcastChannel | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (worldChannel) {
    return worldChannel;
  }
  try {
    worldChannel = new BroadcastChannel(WORLD_CHANNEL);
  } catch {
    worldChannel = null;
  }
  return worldChannel;
}

export function announceWorld(kind: string, extra?: Record<string, unknown>): void {
  if (typeof window === "undefined") {
    return;
  }
  const detail = { kind, ...extra };
  channel()?.postMessage(detail);
  window.dispatchEvent(new CustomEvent("manobal-live", { detail }));
  if (window.parent !== window) {
    window.parent.postMessage({ type: "manobal.stage.event", ...detail }, window.location.origin);
  }
}

export function subscribeWorld(onEvent: (detail: Record<string, unknown>) => void): () => void {
  const socket = channel();
  const onMessage = (event: MessageEvent) => {
    if (event.data && typeof event.data === "object") {
      onEvent(event.data as Record<string, unknown>);
    }
  };
  const onLive = (event: Event) => {
    const custom = event as CustomEvent<Record<string, unknown>>;
    if (custom.detail) {
      onEvent(custom.detail);
    }
  };
  socket?.addEventListener("message", onMessage);
  window.addEventListener("manobal-live", onLive);
  return () => {
    socket?.removeEventListener("message", onMessage);
    window.removeEventListener("manobal-live", onLive);
  };
}
