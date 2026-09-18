"use client";

import { useEffect } from "react";

import { startRealtime } from "@/lib/realtime";

export function LiveObserver() {
  useEffect(() => startRealtime(), []);
  return null;
}
