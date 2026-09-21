"use client";

import { usePersonnelI18n } from "@/lib/personnel-i18n";

export default function Loading() {
  const { p } = usePersonnelI18n();
  return <p role="status">{p("Loading.")}</p>;
}
