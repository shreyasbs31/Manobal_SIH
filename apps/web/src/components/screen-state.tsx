"use client";

import type { ReactNode } from "react";

import { useOptionalPersonnelI18n } from "@/lib/personnel-i18n";

export function ScreenState({
  loading,
  error,
  offline,
  empty,
  emptyText,
  loadingText,
  offlineText,
  children,
}: {
  loading: boolean;
  error: string | null;
  offline: boolean;
  empty?: boolean;
  emptyText?: string;
  loadingText?: string;
  offlineText?: string;
  children: ReactNode;
}) {
  const personnel = useOptionalPersonnelI18n();
  const resolvedEmpty = emptyText ?? personnel?.p("Nothing here yet.") ?? "Nothing here yet.";
  const resolvedLoading = loadingText ?? personnel?.p("Loading.") ?? "Loading.";
  const resolvedOffline =
    offlineText ??
    personnel?.p("Offline. This view stays on the phone after you open it once.") ??
    "Offline. This view stays on the phone after you open it once.";
  if (loading && empty) {
    return <p role="status">{resolvedLoading}</p>;
  }
  if (error && empty) {
    return <p role="alert">{error}</p>;
  }
  if (empty) {
    return (
      <p role="status">
        {offline ? resolvedOffline : resolvedEmpty}
      </p>
    );
  }
  return children;
}
