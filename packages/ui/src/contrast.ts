/**
 * UI Direction v3 palette and WCAG 2.2 contrast helpers.
 * Spec hues stay in specPalette. Semantic roles may shift lightness per theme.
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
  kind: "text" | "glyph" = "text",
): boolean {
  const ratio = contrastRatio(foreground, background);
  return kind === "text" ? ratio >= 4.5 : ratio >= 3;
}

export const specPalette = {
  neem: "#2F5D50",
  neemDeep: "#1F4238",
  mist: "#F4F8F6",
  contour: "#CFDDD6",
  duskInk: "#1B2427",
  dawn: "#F2C6A0",
  monsoon: "#131C24",
  slatePanel: "#1B2630",
  mapLine: "#2A3945",
  brass: "#C8A24A",
  khaki: "#BFB28A",
  chalk: "#E8ECE9",
  surveyBg: "#EEF1EB",
  surveyPanel: "#F8FAF6",
  surveyMap: "#CBD3C8",
  surveyBrass: "#8F6F1E",
  t0: "#6E927F",
  t1: "#4D8BAE",
  t2: "#D6A13D",
  t2StrokeLight: "#9A6F12",
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
  axis: string;
}

export const themes: Record<ThemeId, ThemeColors> = {
  "saathi-light": {
    bg: specPalette.mist,
    surface: "#FFFFFF",
    surface2: specPalette.contour,
    text: specPalette.duskInk,
    muted: "#3D4F48",
    primary: specPalette.neem,
    onPrimary: "#FFFFFF",
    accent: specPalette.neemDeep,
    border: specPalette.contour,
    focus: specPalette.neem,
    sos: specPalette.t4,
    onSos: "#FFFFFF",
    axis: "#5A6B64",
  },
  "saathi-dark": {
    bg: "#12211C",
    surface: specPalette.neemDeep,
    surface2: "#274A40",
    text: specPalette.chalk,
    muted: "#B7C9C1",
    primary: "#8FBEAD",
    onPrimary: "#12211C",
    accent: "#E2C56C",
    border: "#355048",
    focus: "#E2C56C",
    sos: "#E06A5C",
    onSos: "#140706",
    axis: "#9BB0A8",
  },
  "saathi-hc": {
    bg: "#FFFFFF",
    surface: "#FFFFFF",
    surface2: "#EEF2F0",
    text: "#0B0D0E",
    muted: specPalette.duskInk,
    primary: specPalette.neemDeep,
    onPrimary: "#FFFFFF",
    accent: "#5C4708",
    border: "#0B0D0E",
    focus: "#0B0D0E",
    sos: "#8E241C",
    onSos: "#FFFFFF",
    axis: specPalette.duskInk,
  },
  "command-dark": {
    bg: specPalette.monsoon,
    surface: specPalette.slatePanel,
    surface2: specPalette.mapLine,
    text: specPalette.chalk,
    muted: specPalette.khaki,
    primary: specPalette.brass,
    onPrimary: specPalette.monsoon,
    accent: specPalette.brass,
    border: specPalette.mapLine,
    focus: specPalette.brass,
    sos: specPalette.t4,
    onSos: "#FFFFFF",
    axis: specPalette.khaki,
  },
  "command-light": {
    bg: specPalette.surveyBg,
    surface: specPalette.surveyPanel,
    surface2: specPalette.surveyMap,
    text: specPalette.duskInk,
    muted: "#3E4A3F",
    primary: specPalette.surveyBrass,
    onPrimary: "#FFFFFF",
    accent: specPalette.surveyBrass,
    border: specPalette.surveyMap,
    focus: specPalette.surveyBrass,
    sos: specPalette.t4,
    onSos: "#FFFFFF",
    axis: "#3E4A3F",
  },
};

export type TierToken = "t0" | "t1" | "t2" | "t3" | "t4";

export const themeTiers: Record<ThemeId, Record<TierToken, string>> = {
  "saathi-light": {
    t0: specPalette.t0,
    t1: specPalette.t1,
    t2: specPalette.t2StrokeLight,
    t3: specPalette.t3,
    t4: specPalette.t4,
  },
  "saathi-dark": {
    t0: specPalette.t0,
    t1: "#62A4C4",
    t2: specPalette.t2,
    t3: specPalette.t3,
    t4: "#E06A5C",
  },
  "saathi-hc": {
    t0: "#3F6B5C",
    t1: "#2F6A8C",
    t2: specPalette.t2StrokeLight,
    t3: "#A84A1C",
    t4: "#8E241C",
  },
  "command-dark": {
    t0: specPalette.t0,
    t1: specPalette.t1,
    t2: specPalette.t2,
    t3: specPalette.t3,
    t4: "#E06A5C",
  },
  "command-light": {
    t0: specPalette.t0,
    t1: specPalette.t1,
    t2: specPalette.t2StrokeLight,
    t3: specPalette.t3,
    t4: specPalette.t4,
  },
};

const THEME_IDS = [
  "saathi-light",
  "saathi-dark",
  "saathi-hc",
  "command-dark",
  "command-light",
] as const;

const TEXT_KEYS = ["text", "muted", "onPrimary", "onSos"] as const;

export const textPairings: readonly {
  theme: ThemeId;
  fg: keyof ThemeColors;
  bg: keyof ThemeColors;
  kind: "text" | "glyph";
}[] = THEME_IDS.flatMap((theme) => {
  const rows: {
    theme: ThemeId;
    fg: keyof ThemeColors;
    bg: keyof ThemeColors;
    kind: "text" | "glyph";
  }[] = [
    { theme, fg: "text", bg: "bg", kind: "text" },
    { theme, fg: "text", bg: "surface", kind: "text" },
    { theme, fg: "muted", bg: "bg", kind: "text" },
    { theme, fg: "muted", bg: "surface", kind: "text" },
    { theme, fg: "onPrimary", bg: "primary", kind: "text" },
    { theme, fg: "onSos", bg: "sos", kind: "text" },
    { theme, fg: "focus", bg: "bg", kind: "glyph" },
    { theme, fg: "primary", bg: "bg", kind: "glyph" },
  ];
  return rows;
});

export const glyphPairings: readonly {
  theme: ThemeId;
  tier: TierToken;
  background: keyof ThemeColors;
}[] = THEME_IDS.flatMap((theme) =>
  (["t0", "t1", "t2", "t3", "t4"] as const).flatMap((tier) => [
    { theme, tier, background: "bg" as const },
    { theme, tier, background: "surface" as const },
  ]),
);

void TEXT_KEYS;
