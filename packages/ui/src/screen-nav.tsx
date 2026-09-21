"use client";

import { ChevronLeft, X } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";

const ICON_STROKE = 1.75;

export function parentHref(pathname: string, homeHref: string): string {
  if (pathname === homeHref || pathname === "/") {
    return homeHref;
  }
  if (pathname.startsWith("/welfare/cases/")) {
    return "/welfare";
  }
  if (pathname.startsWith("/app/toolkit/")) {
    return "/app/toolkit";
  }
  if (pathname.startsWith("/app/assessments/")) {
    return "/app/assessments";
  }
  if (pathname.startsWith("/command/") && pathname !== "/command") {
    return "/command";
  }
  if (pathname.startsWith("/app/") && pathname !== "/app") {
    return "/app";
  }
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length <= 1) {
    return homeHref;
  }
  parts.pop();
  return `/${parts.join("/")}` || homeHref;
}

function readStack(key: string): string[] {
  try {
    const raw = sessionStorage.getItem(key);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function writeStack(key: string, stack: string[]) {
  sessionStorage.setItem(key, JSON.stringify(stack.slice(-40)));
}

function returningKey(storageKey: string): string {
  return `manobal.nav.returning.${storageKey}`;
}

export function popPathStack(storageKey: string, pathname: string, homeHref: string): string {
  const stack = readStack(storageKey);
  if (stack[stack.length - 1] === pathname) {
    stack.pop();
  }
  const prev = stack[stack.length - 1] ?? parentHref(pathname, homeHref);
  writeStack(storageKey, stack.length ? stack : [prev]);
  sessionStorage.setItem(returningKey(storageKey), "1");
  return prev;
}

export function resetPathStack(storageKey: string, homeHref: string): string {
  writeStack(storageKey, [homeHref]);
  sessionStorage.setItem(returningKey(storageKey), "1");
  return homeHref;
}

export function usePathStack(storageKey: string, pathname: string | null, homeHref: string) {
  const [canBack, setCanBack] = useState(false);

  useEffect(() => {
    if (!pathname) {
      return;
    }
    const flag = returningKey(storageKey);
    const returning = sessionStorage.getItem(flag) === "1";
    if (returning) {
      sessionStorage.removeItem(flag);
    }
    const stack = readStack(storageKey);
    if (!returning && stack[stack.length - 1] !== pathname) {
      stack.push(pathname);
      writeStack(storageKey, stack);
    }
    const next = readStack(storageKey);
    setCanBack(next.length > 1 || pathname !== homeHref);
  }, [pathname, storageKey, homeHref]);

  const back = useCallback(() => {
    return popPathStack(storageKey, pathname ?? homeHref, homeHref);
  }, [homeHref, pathname, storageKey]);

  const close = useCallback(() => {
    return resetPathStack(storageKey, homeHref);
  }, [homeHref, storageKey]);

  return {
    atHome: pathname === homeHref,
    canBack,
    back,
    close,
  };
}

export function requestScreenBack(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const event = new CustomEvent("manobal-screen-back", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

export function goHref(href: string, onNavigate?: (href: string) => void) {
  if (onNavigate) {
    onNavigate(href);
    return;
  }
  if (typeof window === "undefined") {
    return;
  }
  const event = new CustomEvent("manobal.navigate", { cancelable: true, detail: { href } });
  window.dispatchEvent(event);
  if (event.defaultPrevented) {
    return;
  }
  window.location.assign(href);
}

export function ScreenNav({
  showBack,
  showClose,
  onBack,
  onClose,
  compact = false,
  title,
  meta,
  end,
  backLabel = "Back",
  closeLabel = "Close",
}: {
  showBack: boolean;
  showClose: boolean;
  onBack: () => void;
  onClose: () => void;
  compact?: boolean | undefined;
  title?: string | undefined;
  meta?: string | undefined;
  end?: ReactNode;
  backLabel?: string | undefined;
  closeLabel?: string | undefined;
}) {
  if (!showBack && !showClose && !title && !meta && !end) {
    return null;
  }
  const backButton = showBack ? (
    <button
      aria-label={backLabel}
      className="mb-ghost mb-screen-nav-btn"
      onClick={onBack}
      type="button"
    >
      <ChevronLeft aria-hidden="true" size={22} strokeWidth={ICON_STROKE} />
    </button>
  ) : (
    <span aria-hidden="true" className="mb-screen-nav-spacer" />
  );
  const closeButton = showClose ? (
    <button
      aria-label={closeLabel}
      className="mb-ghost mb-screen-nav-btn mb-screen-close"
      onClick={onClose}
      type="button"
    >
      <X aria-hidden="true" size={22} strokeWidth={ICON_STROKE} />
    </button>
  ) : (
    <span aria-hidden="true" className="mb-screen-nav-spacer" />
  );
  if (compact) {
    return (
      <div className="mb-screen-nav" data-compact="true">
        {showBack ? backButton : null}
        {showClose ? closeButton : null}
      </div>
    );
  }
  return (
    <div className="mb-screen-nav" data-compact="false">
      {backButton}
      {title || meta ? (
        <div className="mb-screen-nav-title">
          {title ? <p>{title}</p> : null}
          {meta ? <span>{meta}</span> : null}
        </div>
      ) : (
        <span aria-hidden="true" className="mb-screen-nav-grow" />
      )}
      <div className="mb-screen-nav-end">
        {end}
        {closeButton}
      </div>
    </div>
  );
}
