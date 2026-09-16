/**
 * WCAG 2.2 relative luminance and contrast helpers.
 * Pairings are checked in scripts/check-contrast.mjs and tests/contrast.test.mjs.
 */

export function hexToRgb(hex: string): readonly [number, number, number] {
  const value = hex.replace("#", "");
  if (value.length !== 6) {
    throw new Error(`Expected a 6-digit hex colour, received ${hex}`);
  }
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ];
}

export function relativeLuminance(hex: string): number {
  const channel = (raw: number): number => {
    const sample = raw / 255;
    return sample <= 0.04045
      ? sample / 12.92
      : ((sample + 0.055) / 1.055) ** 2.4;
  };
  const [red, green, blue] = hexToRgb(hex);
  return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue);
}

export function contrastRatio(foreground: string, background: string): number {
  const lighter = Math.max(
    relativeLuminance(foreground),
    relativeLuminance(background),
  );
  const darker = Math.min(
    relativeLuminance(foreground),
    relativeLuminance(background),
  );
  return (lighter + 0.05) / (darker + 0.05);
}

export function passesAa(
  foreground: string,
  background: string,
  kind: "text" | "large" | "ui" = "text",
): boolean {
  const ratio = contrastRatio(foreground, background);
  if (kind === "text") {
    return ratio >= 4.5;
  }
  return ratio >= 3;
}

export const specPalette = {
  neem700: "#2F5D50",
  neem100: "#E4EFEA",
  mist50: "#F5F8F7",
  monsoon950: "#131C24",
  monsoon800: "#1E2A35",
  brass400: "#C8A24A",
  khaki300: "#C9BB8E",
  ink900: "#1B2127",
  t0: "#6E927F",
  t1: "#4D8BAE",
  t2: "#D6A13D",
  t3: "#D06A34",
  t4: "#B83A2E",
} as const;

export type ThemeId =
  | "saathi-light"
  | "saathi-dark"
  | "saathi-hc"
  | "command-dark"
  | "command-light";

export interface ThemeColors {
  bg: string;
  surface: string;
  surface2: string;
  text: string;
  muted: string;
  primary: string;
  onPrimary: string;
  accent: string;
  border: string;
  focus: string;
  sos: string;
  onSos: string;
}

/**
 * Lightness is adjusted per theme so body text and primary buttons meet WCAG AA.
 * Spec hex values stay as the named palette; semantic roles may use a nearby step.
 */
export const themes: Record<ThemeId, ThemeColors> = {
  "saathi-light": {
    bg: specPalette.mist50,
    surface: "#FFFFFF",
    surface2: specPalette.neem100,
    text: specPalette.ink900,
    muted: "#3D4F48",
    primary: specPalette.neem700,
    onPrimary: specPalette.mist50,
    accent: "#8A6A1C",
    border: "#C5D4CE",
    focus: specPalette.neem700,
    sos: specPalette.t4,
    onSos: "#FFFFFF",
  },
  "saathi-dark": {
    bg: "#0E1714",
    surface: "#17241F",
    surface2: "#20322C",
    text: "#E8F3EE",
    muted: "#B7C9C1",
    primary: "#8FBEAD",
    onPrimary: "#0E1714",
    accent: "#E2C56C",
    border: "#355048",
    focus: "#E2C56C",
    sos: "#E06A5C",
    onSos: "#140706",
  },
  "saathi-hc": {
    bg: "#FFFFFF",
    surface: "#FFFFFF",
    surface2: "#EEF2F0",
    text: "#0B0D0E",
    muted: "#1B2127",
    primary: "#16352E",
    onPrimary: "#FFFFFF",
    accent: "#5C4708",
    border: "#0B0D0E",
    focus: "#0B0D0E",
    sos: "#8E241C",
    onSos: "#FFFFFF",
  },
  "command-dark": {
    bg: specPalette.monsoon950,
    surface: specPalette.monsoon800,
    surface2: "#263440",
    text: "#F3F1EA",
    muted: "#D4C8A0",
    primary: "#D7B45E",
    onPrimary: specPalette.monsoon950,
    accent: specPalette.brass400,
    border: "#3A4A57",
    focus: specPalette.brass400,
    sos: specPalette.t4,
    onSos: "#FFFFFF",
  },
  "command-light": {
    bg: "#F3EEE4",
    surface: "#FFFBF4",
    surface2: "#E8E0D0",
    text: specPalette.monsoon950,
    muted: "#3E3A32",
    primary: "#6B5210",
    onPrimary: "#FFFBF4",
    accent: "#8A6A1C",
    border: "#C9BFA8",
    focus: "#6B5210",
    sos: specPalette.t4,
    onSos: "#FFFFFF",
  },
};

export const textPairings: readonly {
  theme: ThemeId;
  fg: keyof ThemeColors;
  bg: keyof ThemeColors;
  kind: "text" | "large" | "ui";
}[] = [
  { theme: "saathi-light", fg: "text", bg: "bg", kind: "text" },
  { theme: "saathi-light", fg: "text", bg: "surface", kind: "text" },
  { theme: "saathi-light", fg: "text", bg: "surface2", kind: "text" },
  { theme: "saathi-light", fg: "muted", bg: "bg", kind: "text" },
  { theme: "saathi-light", fg: "onPrimary", bg: "primary", kind: "text" },
  { theme: "saathi-light", fg: "onSos", bg: "sos", kind: "text" },
  { theme: "saathi-light", fg: "primary", bg: "bg", kind: "ui" },
  { theme: "saathi-dark", fg: "text", bg: "bg", kind: "text" },
  { theme: "saathi-dark", fg: "text", bg: "surface", kind: "text" },
  { theme: "saathi-dark", fg: "muted", bg: "bg", kind: "text" },
  { theme: "saathi-dark", fg: "onPrimary", bg: "primary", kind: "text" },
  { theme: "saathi-dark", fg: "onSos", bg: "sos", kind: "text" },
  { theme: "saathi-hc", fg: "text", bg: "bg", kind: "text" },
  { theme: "saathi-hc", fg: "muted", bg: "bg", kind: "text" },
  { theme: "saathi-hc", fg: "onPrimary", bg: "primary", kind: "text" },
  { theme: "saathi-hc", fg: "onSos", bg: "sos", kind: "text" },
  { theme: "command-dark", fg: "text", bg: "bg", kind: "text" },
  { theme: "command-dark", fg: "text", bg: "surface", kind: "text" },
  { theme: "command-dark", fg: "muted", bg: "bg", kind: "text" },
  { theme: "command-dark", fg: "onPrimary", bg: "primary", kind: "text" },
  { theme: "command-light", fg: "text", bg: "bg", kind: "text" },
  { theme: "command-light", fg: "text", bg: "surface", kind: "text" },
  { theme: "command-light", fg: "muted", bg: "bg", kind: "text" },
  { theme: "command-light", fg: "onPrimary", bg: "primary", kind: "text" },
];

export type TierToken = "t0" | "t1" | "t2" | "t3" | "t4";

/**
 * Spec hex values stay in specPalette. Glyphs are lightened or darkened per
 * theme so each pairing meets a 3:1 UI contrast floor on that theme's surface.
 */
export const themeTiers: Record<ThemeId, Record<TierToken, string>> = {
  "saathi-light": {
    t0: specPalette.t0,
    t1: specPalette.t1,
    t2: "#B48733",
    t3: specPalette.t3,
    t4: specPalette.t4,
  },
  "saathi-dark": {
    t0: specPalette.t0,
    t1: specPalette.t1,
    t2: specPalette.t2,
    t3: specPalette.t3,
    t4: "#BB4236",
  },
  "saathi-hc": {
    t0: "#3F6B5C",
    t1: "#2F6A8C",
    t2: "#8A6A1C",
    t3: "#A84A1C",
    t4: "#8E241C",
  },
  "command-dark": {
    t0: specPalette.t0,
    t1: specPalette.t1,
    t2: specPalette.t2,
    t3: specPalette.t3,
    t4: "#BF4E43",
  },
  "command-light": {
    t0: "#5A7C6B",
    t1: "#3D7394",
    t2: "#AD8231",
    t3: specPalette.t3,
    t4: specPalette.t4,
  },
};

export const tierOnBackground: readonly {
  theme: ThemeId;
  tier: TierToken;
  background: keyof ThemeColors;
}[] = [
  { theme: "saathi-light", tier: "t0", background: "bg" },
  { theme: "saathi-light", tier: "t1", background: "bg" },
  { theme: "saathi-light", tier: "t2", background: "bg" },
  { theme: "saathi-light", tier: "t3", background: "bg" },
  { theme: "saathi-light", tier: "t4", background: "bg" },
  { theme: "saathi-light", tier: "t2", background: "surface" },
  { theme: "saathi-dark", tier: "t0", background: "bg" },
  { theme: "saathi-dark", tier: "t4", background: "surface" },
  { theme: "saathi-hc", tier: "t0", background: "bg" },
  { theme: "saathi-hc", tier: "t2", background: "bg" },
  { theme: "saathi-hc", tier: "t4", background: "bg" },
  { theme: "command-dark", tier: "t0", background: "bg" },
  { theme: "command-dark", tier: "t1", background: "bg" },
  { theme: "command-dark", tier: "t2", background: "bg" },
  { theme: "command-dark", tier: "t3", background: "bg" },
  { theme: "command-dark", tier: "t4", background: "bg" },
  { theme: "command-dark", tier: "t4", background: "surface" },
  { theme: "command-light", tier: "t0", background: "bg" },
  { theme: "command-light", tier: "t1", background: "bg" },
  { theme: "command-light", tier: "t2", background: "bg" },
  { theme: "command-light", tier: "t3", background: "bg" },
  { theme: "command-light", tier: "t4", background: "bg" },
];
