"use client";

import { ManobalApiError, type ManobalClient } from "@manobal/contracts";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  askParentForStageRole,
  currentAccessToken,
  currentPrincipal,
  engineClient,
  ensureDeskRole,
  inStageFrame,
  stageRoleReady,
} from "@/lib/engine";
import { loadSnapshot, saveSnapshot } from "@/lib/offline";
import { principalMatchesPath } from "@/lib/stage-role";
import { subscribeWorld } from "@/lib/world";

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
  const pathname = usePathname();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(
    typeof navigator !== "undefined"
      ? !navigator.onLine || window.localStorage.getItem("manobal.airplane") === "1"
      : false,
  );
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  const settledRef = useRef(false);
  const remintAttempted = useRef(false);
  const lastPathRef = useRef(pathname);
  loaderRef.current = loader;

  useEffect(() => {
    const onOffline = () => setOffline(true);
    const onOnline = () =>
      setOffline(window.localStorage.getItem("manobal.airplane") === "1" ? true : false);
    const onAirplane = () =>
      setOffline(
        window.localStorage.getItem("manobal.airplane") === "1" || !window.navigator.onLine,
      );
    const onStorage = (event: StorageEvent) => {
      if (event.key === "manobal.airplane") {
        onAirplane();
      }
    };
    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);
    window.addEventListener("manobal-airplane", onAirplane);
    window.addEventListener("storage", onStorage);
    const onSession = () => setTick((value) => value + 1);
    window.addEventListener("manobal-session", onSession);
    const stopWorld = subscribeWorld((detail) => {
      if (detail.kind === "airplane") {
        onAirplane();
      }
      setTick((value) => value + 1);
    });
    const poll = inStageFrame()
      ? window.setInterval(() => {
          if (settledRef.current && currentAccessToken() && stageRoleReady(window.location.pathname)) {
            setTick((value) => value + 1);
          }
        }, 4000)
      : null;
    return () => {
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("manobal-airplane", onAirplane);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("manobal-session", onSession);
      stopWorld();
      if (poll !== null) {
        window.clearInterval(poll);
      }
    };
  }, []);

  useEffect(() => {
    if (lastPathRef.current !== pathname) {
      lastPathRef.current = pathname;
      settledRef.current = false;
      remintAttempted.current = false;
    }
    if (inStageFrame() && !stageRoleReady(pathname)) {
      askParentForStageRole(pathname);
      setLoading(true);
      setError(null);
      return;
    }
    const controller = new AbortController();
    let timedOut = false;
    let waitingForRole = false;
    let watchdog = 0;
    void (async () => {
      if (!inStageFrame() && !principalMatchesPath(currentPrincipal()?.role, pathname)) {
        setLoading(true);
        setError(null);
        remintAttempted.current = true;
        const ready = await ensureDeskRole(pathname);
        if (controller.signal.aborted) {
          return;
        }
        if (!ready) {
          setError("The session does not have the required scope");
          setLoading(false);
          return;
        }
      }
      watchdog = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, 12000);
      if (!settledRef.current) {
        setLoading(true);
      }
      setError(null);
      const airplane = window.localStorage.getItem("manobal.airplane") === "1";
      const networkDown = !navigator.onLine || airplane;
      const cached = await loadSnapshot<T>(key);
      if (controller.signal.aborted && !timedOut) {
        return;
      }
      if (cached) {
        setData(cached);
        if (timedOut) {
          setLoading(false);
        }
      }
      if (networkDown) {
        setOffline(true);
        setLoading(false);
        window.clearTimeout(watchdog);
        return;
      }
      try {
        const payload = await loaderRef.current(engineClient(), controller.signal);
        if (!controller.signal.aborted) {
          setData(payload);
          void saveSnapshot(key, payload);
        }
      } catch (caught: unknown) {
        if (controller.signal.aborted) {
          if (timedOut && !settledRef.current) {
            setError("Could not load this screen");
            setLoading(false);
          }
          return;
        }
        if (
          inStageFrame() &&
          caught instanceof ManobalApiError &&
          (caught.status === 403 || caught.status === 401)
        ) {
          waitingForRole = true;
          askParentForStageRole(pathname);
          setError(null);
          setLoading(true);
          settledRef.current = false;
          return;
        }
        if (
          !inStageFrame() &&
          !remintAttempted.current &&
          caught instanceof ManobalApiError &&
          (caught.status === 403 || caught.status === 401) &&
          !principalMatchesPath(currentPrincipal()?.role, pathname)
        ) {
          remintAttempted.current = true;
          waitingForRole = true;
          settledRef.current = false;
          const ready = await ensureDeskRole(pathname);
          if (ready && !controller.signal.aborted) {
            setTick((value) => value + 1);
          } else if (!controller.signal.aborted) {
            setError(caught.message);
            setLoading(false);
          }
          return;
        }
        if (caught instanceof ManobalApiError) {
          setError(caught.message);
        } else if (caught instanceof Error) {
          setError(caught.message);
        } else {
          setError("Could not load this screen");
        }
      } finally {
        window.clearTimeout(watchdog);
        if (!controller.signal.aborted && !waitingForRole) {
          settledRef.current = true;
          setLoading(false);
        }
      }
    })();
    return () => {
      window.clearTimeout(watchdog);
      controller.abort();
    };
  }, [key, tick, pathname]);

  return {
    data,
    error,
    loading,
    offline,
    reload: () => setTick((value) => value + 1),
  };
}
