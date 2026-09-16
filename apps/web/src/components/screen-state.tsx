"use client";

import type { ReactNode } from "react";

export function ScreenState({
  loading,
  error,
  offline,
  empty,
  emptyText = "Nothing here yet.",
  children,
}: {
  loading: boolean;
  error: string | null;
  offline: boolean;
  empty?: boolean;
  emptyText?: string;
  children: ReactNode;
}) {
  if (offline) {
    return <p role="status">Offline. Reconnect to load this view.</p>;
  }
  if (loading) {
    return <p role="status">Loading.</p>;
  }
  if (error) {
    return <p role="alert">{error}</p>;
  }
  if (empty) {
    return <p role="status">{emptyText}</p>;
  }
  return children;
}
