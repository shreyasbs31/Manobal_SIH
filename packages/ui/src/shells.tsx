"use client";

import { Command } from "cmdk";
import {
  CalendarRange,
  Clapperboard,
  FlaskConical,
  House,
  Inbox,
  Layers,
  LayoutGrid,
  MessageCircle,
  PanelLeft,
  Phone,
  Scale,
  Search,
  Settings,
  Shield,
  Stethoscope,
  User,
  Volume2,
  VolumeX,
  Wrench,
} from "lucide-react";
import {
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useState,
} from "react";

import { ModeChip, SimClock, StatusChip } from "./badges";
import { RibbonMark, SyntheticMarker } from "./brand";
import { SOSButton } from "./companion";
import { goHref, requestScreenBack, ScreenNav, usePathStack } from "./screen-nav";
import { setSoundEnabled, soundEnabled } from "./sound";
import { ContourTexture, MapGrid } from "./texture-view";
import type { ManobalMode, ThemeName } from "./types";

export interface NavItem {
  href: string;
  label: string;
}

const SAATHI_TABS: readonly NavItem[] = [
  { href: "/app", label: "Home" },
  { href: "/app/saathi", label: "Saathi" },
  { href: "/app/toolkit", label: "Toolkit" },
  { href: "/app/me", label: "Me" },
];

const TAB_ICONS = [House, MessageCircle, Wrench, User] as const;
const ICON_STROKE = 1.75;

export function SaathiShell({
  children,
  pathname,
  greeting = "Saathi",
  shiftLine,
  offline = false,
  queued = 0,
  syncing = false,
  mode = "demo",
  chrome = "full",
  simple = false,
  flowLabel,
  flowMeta,
  homeHref = "/app",
  onNavigate,
}: {
  children: ReactNode;
  pathname: string;
  greeting?: string | undefined;
  shiftLine?: string | undefined;
  offline?: boolean | undefined;
  queued?: number | undefined;
  syncing?: boolean | undefined;
  mode?: ManobalMode | undefined;
  chrome?: "full" | "flow" | "none" | undefined;
  simple?: boolean | undefined;
  flowLabel?: string | undefined;
  flowMeta?: string | undefined;
  homeHref?: string | undefined;
  onNavigate?: ((href: string) => void) | undefined;
}) {
  const isHome = pathname === homeHref;
  const nav = usePathStack("manobal.nav.saathi", pathname, homeHref);
  const showTabs = chrome === "full";
  const showInnerNav = chrome !== "none" && !isHome;

  const goBack = useCallback(() => {
    if (requestScreenBack()) {
      return;
    }
    goHref(nav.back(), onNavigate);
  }, [nav, onNavigate]);

  const goClose = useCallback(() => {
    goHref(nav.close(), onNavigate);
  }, [nav, onNavigate]);

  useEffect(() => {
    if (chrome === "none") {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.metaKey || event.ctrlKey) {
        return;
      }
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
      ) {
        return;
      }
      if (showInnerNav) {
        event.preventDefault();
        goBack();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chrome, goBack, showInnerNav]);

  if (chrome === "none") {
    return <>{children}</>;
  }

  return (
    <div
      className="mb-theme mb-saathi"
      data-chrome={chrome}
      data-home={isHome ? "true" : "false"}
      data-simple={simple ? "true" : "false"}
      data-skin="saathi"
      data-theme="light"
    >
      <a className="mb-skip" href="#main">
        Skip to content
      </a>
      <header className="mb-saathi-top" aria-label="Saathi">
        {isHome && chrome === "full" ? (
          <>
            <div className="mb-saathi-greet">
              <h1 className="mb-type-hero">{greeting}</h1>
              {shiftLine ? <p className="mb-saathi-shift">{shiftLine}</p> : null}
            </div>
            <SOSButton href="/app/safety" />
          </>
        ) : (
          <>
            <h1 className="mb-sr-only">{flowLabel || "Saathi"}</h1>
            <ScreenNav
              meta={flowMeta}
              onBack={goBack}
              onClose={goClose}
              showBack
              showClose
              title={flowLabel}
            />
          </>
        )}
        {showTabs && isHome ? (
          <div className="mb-saathi-status">
            {offline ? <StatusChip kind="offline" queued={queued} /> : null}
            {syncing ? <StatusChip kind="syncing" /> : null}
            {mode === "demo" ? <StatusChip kind="demo" /> : null}
          </div>
        ) : null}
      </header>
      <main className="mb-saathi-main" id="main" aria-label="Saathi content">
        {children}
      </main>
      {showTabs ? (
        <nav className="mb-saathi-tabs" aria-label="Saathi">
          {SAATHI_TABS.map((tab, index) => {
            const Icon = TAB_ICONS[index] ?? House;
            const current =
              tab.href === "/app"
                ? pathname === "/app"
                : pathname === tab.href || pathname.startsWith(`${tab.href}/`);
            return (
              <a
                aria-current={current ? "page" : undefined}
                href={tab.href}
                key={tab.href}
              >
                <Icon aria-hidden="true" size={20} strokeWidth={ICON_STROKE} />
                {tab.label}
              </a>
            );
          })}
        </nav>
      ) : null}
    </div>
  );
}

const DEFAULT_COMMAND_NAV: readonly NavItem[] = [
  { href: "/command", label: "Unit posture" },
  { href: "/command/roster", label: "Roster balancer" },
  { href: "/welfare", label: "Welfare queue" },
  { href: "/medical", label: "Acute board" },
  { href: "/hq", label: "Force HQ" },
  { href: "/governance", label: "Governance" },
  { href: "/lab", label: "Validation lab" },
  { href: "/architecture", label: "Architecture" },
];

const RAIL_ICONS: Record<string, typeof LayoutGrid> = {
  "/command": LayoutGrid,
  "/command/roster": CalendarRange,
  "/welfare": Inbox,
  "/counsel": Phone,
  "/medical": Stethoscope,
  "/hq": Layers,
  "/governance": Scale,
  "/dpo": Shield,
  "/integrations": Settings,
  "/admin": Wrench,
  "/lab": FlaskConical,
  "/architecture": Layers,
  "/director": Clapperboard,
};

export function CommandShell({
  children,
  pathname,
  title,
  navItems = DEFAULT_COMMAND_NAV,
  units = ["Bn C-02", "Charlie Coy", "Alpha Coy"],
  mode = "demo",
  clock = "2026-09-16 10:00 IST",
  theme = "light",
  deskLabel,
  onNavigate,
  homeHref = "/command",
  language = "en",
  onLanguageChange,
  chromeCopy,
}: {
  children: ReactNode;
  pathname: string;
  title: string;
  navItems?: readonly NavItem[] | undefined;
  units?: readonly string[] | undefined;
  mode?: ManobalMode | undefined;
  clock?: string | undefined;
  theme?: Extract<ThemeName, "dark" | "light"> | undefined;
  deskLabel?: string | undefined;
  onNavigate?: ((href: string) => void) | undefined;
  homeHref?: string | undefined;
  language?: "en" | "hi" | undefined;
  onLanguageChange?: ((lang: "en" | "hi") => void) | undefined;
  chromeCopy?:
    | {
        expand: string;
        collapse: string;
        search: string;
        themeLight: string;
        themeDark: string;
        langEn: string;
        langHi: string;
        langGroup: string;
        deskSuffix: string;
      }
    | undefined;
}) {
  const labels = chromeCopy ?? {
    expand: "Expand menu",
    collapse: "Collapse menu",
    search: "Search",
    themeLight: "Survey paper",
    themeDark: "Night panel",
    langEn: "English",
    langHi: "Hindi",
    langGroup: "Console language",
    deskSuffix: "desk",
  };
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [unit, setUnit] = useState(units[0] ?? "Bn C-02");
  const [skinTheme, setSkinTheme] = useState<"dark" | "light">(theme);
  const [soundOn, setSoundOn] = useState(false);
  const paletteId = useId();
  const items = useMemo(() => navItems, [navItems]);
  const nav = usePathStack("manobal.nav.command", pathname, homeHref);
  const goBack = useCallback(() => {
    if (requestScreenBack()) {
      return;
    }
    goHref(nav.back(), onNavigate);
  }, [nav, onNavigate]);
  const goClose = useCallback(() => {
    goHref(nav.close(), onNavigate);
  }, [nav, onNavigate]);
  const showBack = nav.canBack || pathname !== homeHref;
  const showClose = pathname !== homeHref;

  useEffect(() => {
    setSoundOn(soundEnabled());
    const stored = window.sessionStorage.getItem("manobal.console.theme");
    if (stored === "dark" || stored === "light") {
      setSkinTheme(stored);
    }
  }, []);

  const onKey = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      setPaletteOpen((open) => !open);
    }
    if (event.key === "Escape") {
      if (paletteOpen) {
        setPaletteOpen(false);
        return;
      }
      if (showBack) {
        event.preventDefault();
        goBack();
      }
    }
  }, [goBack, paletteOpen, showBack]);

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  return (
    <div
      className="mb-theme mb-command"
      data-collapsed={collapsed ? "true" : "false"}
      data-mode={mode}
      data-skin="command"
      data-theme={skinTheme}
      lang={language}
    >
      <a className="mb-skip" href="#main">
        Skip to content
      </a>
      <nav className="mb-rail" aria-label="Console">
        <div className="mb-rail-texture" aria-hidden="true">
          <ContourTexture height={640} opacity={0.08} seed="command-rail" width={220} />
          <MapGrid />
        </div>
        <div className="mb-brand">
          <RibbonMark title="MANOBAL ribbon" />
          <span className="mb-rail-label">MANOBAL</span>
        </div>
        <button
          className="mb-rail-item"
          onClick={() => setCollapsed((value) => !value)}
          type="button"
        >
          <PanelLeft size={16} strokeWidth={ICON_STROKE} aria-hidden="true" />
          <span className="mb-rail-label">
            {collapsed ? labels.expand : labels.collapse}
          </span>
        </button>
        <div className="mb-rail-scroll">
        {items.map((item) => {
          const current =
            item.href === pathname ||
            (item.href !== "/command" && pathname.startsWith(item.href));
          const Icon = RAIL_ICONS[item.href] ?? LayoutGrid;
          return (
            <a
              aria-current={current ? "page" : undefined}
              href={item.href}
              key={item.href}
              onClick={(event) => {
                if (!onNavigate || event.metaKey || event.ctrlKey || event.shiftKey) {
                  return;
                }
                event.preventDefault();
                onNavigate(item.href);
              }}
            >
              <Icon size={16} strokeWidth={ICON_STROKE} aria-hidden="true" />
              <span className="mb-rail-label">{item.label}</span>
            </a>
          );
        })}
        </div>
        <div className="mb-rail-foot">
          <div className="mb-lang-toggle" role="group" aria-label={labels.langGroup}>
            <button
              aria-label={labels.langEn}
              aria-pressed={language === "en"}
              className="mb-ghost"
              onClick={() => onLanguageChange?.("en")}
              type="button"
            >
              EN
            </button>
            <button
              aria-label={labels.langHi}
              aria-pressed={language === "hi"}
              className="mb-ghost"
              onClick={() => onLanguageChange?.("hi")}
              type="button"
            >
              हि
            </button>
          </div>
          <label className="mb-rail-theme">
            <span className="mb-sr">Theme</span>
            <select
              aria-label="Theme"
              onChange={(event) => {
                const next = event.target.value === "light" ? "light" : "dark";
                setSkinTheme(next);
                if (typeof window !== "undefined") {
                  window.sessionStorage.setItem("manobal.console.theme", next);
                }
              }}
              value={skinTheme}
            >
              <option value="light">{labels.themeLight}</option>
              <option value="dark">{labels.themeDark}</option>
            </select>
          </label>
        </div>
      </nav>
      <div className="mb-command-main">
        <header className="mb-topbar" aria-label={deskLabel ? `${deskLabel} ${labels.deskSuffix}` : "Console"}>
          <div className="mb-topbar-start">
            <ScreenNav
              compact
              onBack={goBack}
              onClose={goClose}
              showBack={showBack}
              showClose={showClose}
            />
            <label className="mb-unit">
              <span className="mb-sr">Unit</span>
              <select
                aria-label="Scoped unit"
                className="mb-unit"
                onChange={(event) => setUnit(event.target.value)}
                value={unit}
              >
                {units.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <h1 className="mb-type-title">{title}</h1>
          </div>
          <div className="mb-topbar-end">
            <SimClock value={clock} />
            <button
              aria-label={soundOn ? "Mute console chimes" : "Enable console chimes"}
              className="mb-ghost"
              onClick={() => {
                const next = !soundOn;
                setSoundEnabled(next);
                setSoundOn(next);
              }}
              type="button"
            >
              {soundOn ? (
                <Volume2 size={16} strokeWidth={ICON_STROKE} />
              ) : (
                <VolumeX size={16} strokeWidth={ICON_STROKE} />
              )}
            </button>
            <button
              aria-expanded={paletteOpen}
              aria-controls={paletteId}
              aria-label={labels.search}
              className="mb-ghost mb-search-btn"
              onClick={() => setPaletteOpen(true)}
              type="button"
            >
              <Search size={16} strokeWidth={ICON_STROKE} aria-hidden="true" />
            </button>
          </div>
        </header>
        <main className="mb-command-body" id="main" aria-label="Console content">
          {children}
        </main>
      </div>
      {paletteOpen ? (
        <div className="mb-cmdk" id={paletteId}>
          <Command label="Open a surface" loop>
            <Command.Input placeholder="Open a surface" />
            <Command.List>
              {items.map((item) => (
                <Command.Item
                  key={item.href}
                  onSelect={() => {
                    setPaletteOpen(false);
                    if (onNavigate) {
                      onNavigate(item.href);
                      return;
                    }
                    window.location.assign(item.href);
                  }}
                  value={item.label}
                >
                  {item.label}
                </Command.Item>
              ))}
            </Command.List>
          </Command>
        </div>
      ) : null}
    </div>
  );
}

export function PublicHeader({
  mode = "demo",
  home = false,
}: {
  mode?: ManobalMode | undefined;
  home?: boolean | undefined;
}) {
  const [path, setPath] = useState<string | null>(null);
  useEffect(() => {
    setPath(window.location.pathname);
  }, []);
  const nav = usePathStack("manobal.nav.public", home ? "/" : path, "/");
  const atHome = home || path === "/" || path === null;
  const goPublicBack = () => goHref(nav.back());

  useEffect(() => {
    if (atHome) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.metaKey || event.ctrlKey) {
        return;
      }
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
      ) {
        return;
      }
      event.preventDefault();
      goPublicBack();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [atHome, path]);

  return (
    <header className="mb-public-header" aria-label="Site">
      <div className="mb-public-start">
        {atHome ? null : (
          <ScreenNav
            compact
            onBack={() => goHref(nav.back())}
            onClose={() => goHref(nav.close())}
            showBack
            showClose
          />
        )}
        <a className="mb-brand" href="/">
          <RibbonMark />
          MANOBAL
        </a>
      </div>
      <div className="mb-public-end">
        <SyntheticMarker />
        <ModeChip mode={mode} />
        <a className="mb-ghost" href="/trust">
          Trust centre
        </a>
        <a className="mb-secondary" href="/login">
          Sign in
        </a>
      </div>
    </header>
  );
}
