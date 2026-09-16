"use client";

import { Command } from "cmdk";
import {
  Bell,
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
}) {
  if (chrome === "none") {
    return <>{children}</>;
  }

  const showTabs = chrome === "full";
  const showGreeting = chrome === "full";

  return (
    <div className="mb-theme mb-saathi" data-skin="saathi" data-theme="light">
      <a className="mb-skip" href="#main">
        Skip to content
      </a>
      <header className="mb-saathi-top" aria-label="Saathi">
        {showGreeting ? (
          <div className="mb-saathi-greet">
            <h1 className="mb-type-hero">{greeting}</h1>
            {shiftLine ? <p className="mb-saathi-shift">{shiftLine}</p> : null}
          </div>
        ) : (
          <a aria-label="Close" className="mb-ghost mb-flow-close" href="/app">
            x
          </a>
        )}
        {chrome === "full" ? <SOSButton href="/app/safety" /> : null}
        {showTabs ? (
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
      <footer>
        <p className="mb-chip mb-chip--synthetic mb-saathi-synthetic">Synthetic data</p>
      </footer>
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
  "/admin": Settings,
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
  theme = "dark",
}: {
  children: ReactNode;
  pathname: string;
  title: string;
  navItems?: readonly NavItem[] | undefined;
  units?: readonly string[] | undefined;
  mode?: ManobalMode | undefined;
  clock?: string | undefined;
  theme?: Extract<ThemeName, "dark" | "light"> | undefined;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [unit, setUnit] = useState(units[0] ?? "Bn C-02");
  const [language, setLanguage] = useState("English");
  const [skinTheme, setSkinTheme] = useState<"dark" | "light">(theme);
  const [soundOn, setSoundOn] = useState(false);
  const paletteId = useId();
  const items = useMemo(() => navItems, [navItems]);

  useEffect(() => {
    setSoundOn(soundEnabled());
  }, []);

  const onKey = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      setPaletteOpen((open) => !open);
    }
    if (event.key === "Escape") {
      setPaletteOpen(false);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  return (
    <div
      className="mb-theme mb-command"
      data-collapsed={collapsed ? "true" : "false"}
      data-skin="command"
      data-theme={skinTheme}
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
            {collapsed ? "Expand menu" : "Collapse menu"}
          </span>
        </button>
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
            >
              <Icon size={16} strokeWidth={ICON_STROKE} aria-hidden="true" />
              <span className="mb-rail-label">{item.label}</span>
            </a>
          );
        })}
      </nav>
      <div className="mb-command-main">
        <header className="mb-topbar" aria-label="Console">
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
          <div className="mb-topbar-end">
            <SimClock value={clock} />
            <ModeChip mode={mode} />
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
            <label>
              <span className="mb-sr">Theme</span>
              <select
                aria-label="Theme"
                onChange={(event) =>
                  setSkinTheme(event.target.value === "light" ? "light" : "dark")
                }
                value={skinTheme}
              >
                <option value="dark">Night panel</option>
                <option value="light">Survey paper</option>
              </select>
            </label>
            <label>
              <span className="mb-sr">Language</span>
              <select
                aria-label="Language"
                onChange={(event) => setLanguage(event.target.value)}
                value={language}
              >
                <option>English</option>
                <option>Hindi</option>
                <option>Tamil</option>
                <option>Urdu</option>
              </select>
            </label>
            <button aria-label="Notifications" className="mb-ghost" type="button">
              <Bell size={16} strokeWidth={ICON_STROKE} />
            </button>
            <button
              aria-expanded={paletteOpen}
              aria-controls={paletteId}
              className="mb-secondary"
              onClick={() => setPaletteOpen(true)}
              type="button"
            >
              <Search size={16} strokeWidth={ICON_STROKE} aria-hidden="true" />
              Search
            </button>
            <SyntheticMarker />
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

export function PublicHeader({ mode = "demo" }: { mode?: ManobalMode | undefined }) {
  return (
    <header className="mb-public-header" aria-label="Site">
      <a className="mb-brand" href="/">
        <RibbonMark />
        MANOBAL
      </a>
      <div className="mb-topbar-end">
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
