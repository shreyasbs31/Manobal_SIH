"use client";

import { useLayoutEffect, useSyncExternalStore } from "react";

let currentMeta = "";
const listeners = new Set<(meta: string) => void>();

export function setFlowMeta(meta: string) {
  currentMeta = meta;
  listeners.forEach((listener) => listener(meta));
}

export function subscribeFlowMeta(listener: (meta: string) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useFlowMeta(meta: string | undefined) {
  useLayoutEffect(() => {
    setFlowMeta(meta ?? "");
    return () => setFlowMeta("");
  }, [meta]);
}

export function useFlowMetaValue(): string {
  return useSyncExternalStore(
    subscribeFlowMeta,
    () => currentMeta,
    () => "",
  );
}
