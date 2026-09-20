"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function NavBridge() {
  const router = useRouter();
  useEffect(() => {
    const onNavigate = (event: Event) => {
      const href = (event as CustomEvent<{ href?: string }>).detail?.href;
      if (!href || !href.startsWith("/") || href.startsWith("//") || href.includes("://")) {
        return;
      }
      event.preventDefault();
      router.push(href);
    };
    window.addEventListener("manobal.navigate", onNavigate);
    return () => window.removeEventListener("manobal.navigate", onNavigate);
  }, [router]);
  return null;
}
