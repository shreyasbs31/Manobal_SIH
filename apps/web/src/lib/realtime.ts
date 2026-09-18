"use client";

import { currentAccessToken, engineClient } from "@/lib/engine";

export function realtimeWebSocketUrl(ticket: string): string {
  if (typeof window === "undefined") {
    return `ws://localhost:8080/?token=${encodeURIComponent(ticket)}`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return `${proto}//${host}:8080/?token=${encodeURIComponent(ticket)}`;
  }
  return `${proto}//${window.location.host}/realtime/?token=${encodeURIComponent(ticket)}`;
}

export function startRealtime(): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  let closed = false;
  let generation = 0;
  let socket: WebSocket | null = null;
  let retry: number | null = null;
  let refresh: number | null = null;

  const disconnect = () => {
    if (retry !== null) {
      window.clearTimeout(retry);
      retry = null;
    }
    if (refresh !== null) {
      window.clearTimeout(refresh);
      refresh = null;
    }
    if (socket) {
      socket.onopen = null;
      socket.onclose = null;
      socket.onerror = null;
      socket.onmessage = null;
      socket.close();
      socket = null;
    }
  };

  const connect = () => {
    if (closed) {
      return;
    }
    const access = currentAccessToken();
    if (!access) {
      disconnect();
      retry = window.setTimeout(connect, 800);
      return;
    }
    const mine = generation + 1;
    generation = mine;
    disconnect();
    void engineClient()
      .realtimeNegotiate()
      .then((ticket) => {
        if (closed || mine !== generation || currentAccessToken() !== access) {
          return;
        }
        const next = new WebSocket(realtimeWebSocketUrl(ticket.token));
        socket = next;
        next.onmessage = (event) => {
          try {
            const payload = JSON.parse(String(event.data)) as { type?: string };
            if (!payload.type || payload.type === "connected") {
              return;
            }
            window.dispatchEvent(new CustomEvent("manobal-live", { detail: payload }));
          } catch {
            // Ignore a malformed hub frame.
          }
        };
        next.onclose = () => {
          if (!closed) {
            retry = window.setTimeout(connect, 1500);
          }
        };
        next.onerror = () => {
          next.close();
        };
        refresh = window.setTimeout(connect, 4 * 60 * 1000);
      })
      .catch(() => {
        if (!closed) {
          retry = window.setTimeout(connect, 2000);
        }
      });
  };

  const onSession = () => {
    connect();
  };
  window.addEventListener("manobal-session", onSession);
  connect();

  return () => {
    closed = true;
    window.removeEventListener("manobal-session", onSession);
    disconnect();
  };
}
