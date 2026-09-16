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
  if (loading && empty) {
    return <p role="status">Loading.</p>;
  }
  if (error && empty) {
    return <p role="alert">{error}</p>;
  }
  if (empty) {
    return (
      <p role="status">
        {offline
          ? "Offline. This view stays on the phone after you open it once."
          : emptyText}
      </p>
    );
  }
  return children;
}
