"use client";

import { ManobalApiError, type ManobalClient } from "@manobal/contracts";
import { useEffect, useRef, useState } from "react";

import { engineClient } from "@/lib/engine";

export function useEngine<T>(
  key: string,
  loader: (client: ManobalClient, signal: AbortSignal) => Promise<T>,
): {
  data: T | null;
  error: string | null;
  loading: boolean;
  offline: boolean;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(
    typeof navigator !== "undefined" ? !navigator.onLine : false,
  );
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    const onOffline = () => setOffline(true);
    const onOnline = () => setOffline(false);
    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);
    return () => {
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    loaderRef
      .current(engineClient(), controller.signal)
      .then((payload) => {
        if (!controller.signal.aborted) {
          setData(payload);
        }
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        if (caught instanceof ManobalApiError) {
          setError(caught.message);
        } else if (caught instanceof Error) {
          setError(caught.message);
        } else {
          setError("Could not load this screen");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [key, tick]);

  return {
    data,
    error,
    loading,
    offline,
    reload: () => setTick((value) => value + 1),
  };
}
