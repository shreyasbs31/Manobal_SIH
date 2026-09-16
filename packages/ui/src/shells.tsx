"use client";

import { Command } from "cmdk";
import {
  Bell,
  CalendarRange,
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
  Sparkles,
  Stethoscope,
  User,
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

import { ModeChip, OfflineChip, SimClock, SyncQueueIndicator } from "./badges";
import { RibbonMark, SyntheticMarker } from "./brand";
import { SOSButton } from "./companion";
import type { ManobalMode } from "./types";

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

export function SaathiShell({
  children,
  pathname,
  greeting = "Saathi",
  offline = false,
  queued = 0,
  lastSync = "Just now",
}: {
  children: ReactNode;
  pathname: string;
  greeting?: string | undefined;
  offline?: boolean | undefined;
  queued?: number | undefined;
  lastSync?: string | undefined;
}) {
  return (
    <div className="mb-theme mb-saathi" data-skin="saathi" data-theme="light">
      <a className="mb-skip" href="#main">
        Skip to content
      </a>
      <header className="mb-saathi-top">
        <div className="mb-brand">
          <RibbonMark />
          <span>{greeting}</span>
        </div>
        <SOSButton href="/app/me" />
      </header>
      <div className="mb-saathi-status">
        <SyntheticMarker />
        <OfflineChip offline={offline} />
        {queued > 0 ? <SyncQueueIndicator count={queued} /> : null}
        <span className="mb-chip">Last sync {lastSync}</span>
      </div>
      <main className="mb-saathi-main" id="main">
        {children}
      </main>
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
              <Icon aria-hidden="true" size={20} />
              {tab.label}
            </a>
          );
        })}
      </nav>
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
  "/director": Sparkles,
};

export function CommandShell({
  children,
  pathname,
  title,
  navItems = DEFAULT_COMMAND_NAV,
  units = ["Synthetic sector North", "Company A", "Company B"],
  mode = "demo",
  clock = "2026-09-16 10:00 IST",
}: {
  children: ReactNode;
  pathname: string;
  title: string;
  navItems?: readonly NavItem[] | undefined;
  units?: readonly string[] | undefined;
  mode?: ManobalMode | undefined;
  clock?: string | undefined;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [unit, setUnit] = useState(units[0] ?? "Synthetic sector North");
  const [language, setLanguage] = useState("English");
  const paletteId = useId();
  const items = useMemo(() => navItems, [navItems]);

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
      data-theme="dark"
    >
      <a className="mb-skip" href="#main">
        Skip to content
      </a>
      <nav className="mb-rail" aria-label="Console">
        <div className="mb-brand">
          <RibbonMark title="MANOBAL ribbon" />
          <span className="mb-rail-label">MANOBAL</span>
        </div>
        <button
          className="mb-rail-item"
          onClick={() => setCollapsed((value) => !value)}
          type="button"
        >
          <PanelLeft size={18} aria-hidden="true" />
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
              <Icon size={18} aria-hidden="true" />
              <span className="mb-rail-label">{item.label}</span>
            </a>
          );
        })}
      </nav>
      <div className="mb-command-main">
        <header className="mb-topbar">
          <label className="mb-unit">
            <span className="mb-rail-label">Unit</span>
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
          <h1 style={{ margin: 0, fontSize: 20 }}>{title}</h1>
          <div className="mb-topbar-end">
            <SimClock value={clock} />
            <ModeChip mode={mode} />
            <label>
              <span className="mb-rail-label">Language</span>
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
              <Bell size={18} />
            </button>
            <button
              aria-expanded={paletteOpen}
              aria-controls={paletteId}
              className="mb-secondary"
              onClick={() => setPaletteOpen(true)}
              type="button"
            >
              <Search size={16} aria-hidden="true" />
              Search
            </button>
            <SyntheticMarker />
          </div>
        </header>
        <main className="mb-command-body" id="main">
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
    <header className="mb-public-header">
      <a className="mb-brand" href="/">
        <RibbonMark />
        MANOBAL
      </a>
      <div className="mb-topbar-end">
        <SyntheticMarker />
        <ModeChip mode={mode} />
        <a className="mb-secondary" href="/login">
          Demo sign-in
        </a>
      </div>
    </header>
  );
}
