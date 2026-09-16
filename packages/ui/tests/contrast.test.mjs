import assert from "node:assert/strict";
import test from "node:test";

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ];
}

function relativeLuminance(hex) {
  const channel = (raw) => {
    const sample = raw / 255;
    return sample <= 0.04045
      ? sample / 12.92
      : ((sample + 0.055) / 1.055) ** 2.4;
  };
  const [red, green, blue] = hexToRgb(hex);
  return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue);
}

function contrastRatio(foreground, background) {
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

const themes = {
  "saathi-light": {
    bg: "#F5F8F7",
    surface: "#FFFFFF",
    surface2: "#E4EFEA",
    text: "#1B2127",
    muted: "#3D4F48",
    primary: "#2F5D50",
    onPrimary: "#F5F8F7",
    sos: "#B83A2E",
    onSos: "#FFFFFF",
  },
  "saathi-dark": {
    bg: "#0E1714",
    surface: "#17241F",
    text: "#E8F3EE",
    muted: "#B7C9C1",
    primary: "#8FBEAD",
    onPrimary: "#0E1714",
    sos: "#E06A5C",
    onSos: "#140706",
  },
  "saathi-hc": {
    bg: "#FFFFFF",
    text: "#0B0D0E",
    muted: "#1B2127",
    primary: "#16352E",
    onPrimary: "#FFFFFF",
    sos: "#8E241C",
    onSos: "#FFFFFF",
  },
  "command-dark": {
    bg: "#131C24",
    surface: "#1E2A35",
    text: "#F3F1EA",
    muted: "#D4C8A0",
    primary: "#D7B45E",
    onPrimary: "#131C24",
    sos: "#B83A2E",
    onSos: "#FFFFFF",
  },
  "command-light": {
    bg: "#F3EEE4",
    surface: "#FFFBF4",
    text: "#131C24",
    muted: "#3E3A32",
    primary: "#6B5210",
    onPrimary: "#FFFBF4",
    sos: "#B83A2E",
    onSos: "#FFFFFF",
  },
};

const themeTiers = {
  "saathi-light": {
    t0: "#6E927F",
    t1: "#4D8BAE",
    t2: "#B48733",
    t3: "#D06A34",
    t4: "#B83A2E",
  },
  "saathi-dark": {
    t0: "#6E927F",
    t1: "#4D8BAE",
    t2: "#D6A13D",
    t3: "#D06A34",
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
    t0: "#6E927F",
    t1: "#4D8BAE",
    t2: "#D6A13D",
    t3: "#D06A34",
    t4: "#BF4E43",
  },
  "command-light": {
    t0: "#5A7C6B",
    t1: "#3D7394",
    t2: "#AD8231",
    t3: "#D06A34",
    t4: "#B83A2E",
  },
};

const textPairings = [
  ["saathi-light", "text", "bg", 4.5],
  ["saathi-light", "text", "surface", 4.5],
  ["saathi-light", "text", "surface2", 4.5],
  ["saathi-light", "muted", "bg", 4.5],
  ["saathi-light", "onPrimary", "primary", 4.5],
  ["saathi-light", "onSos", "sos", 4.5],
  ["saathi-light", "primary", "bg", 3],
  ["saathi-dark", "text", "bg", 4.5],
  ["saathi-dark", "text", "surface", 4.5],
  ["saathi-dark", "muted", "bg", 4.5],
  ["saathi-dark", "onPrimary", "primary", 4.5],
  ["saathi-dark", "onSos", "sos", 4.5],
  ["saathi-hc", "text", "bg", 4.5],
  ["saathi-hc", "muted", "bg", 4.5],
  ["saathi-hc", "onPrimary", "primary", 4.5],
  ["saathi-hc", "onSos", "sos", 4.5],
  ["command-dark", "text", "bg", 4.5],
  ["command-dark", "text", "surface", 4.5],
  ["command-dark", "muted", "bg", 4.5],
  ["command-dark", "onPrimary", "primary", 4.5],
  ["command-light", "text", "bg", 4.5],
  ["command-light", "text", "surface", 4.5],
  ["command-light", "muted", "bg", 4.5],
  ["command-light", "onPrimary", "primary", 4.5],
];

const tierPairings = [
  ["saathi-light", "bg"],
  ["saathi-light", "surface"],
  ["saathi-dark", "bg"],
  ["saathi-dark", "surface"],
  ["saathi-hc", "bg"],
  ["command-dark", "bg"],
  ["command-dark", "surface"],
  ["command-light", "bg"],
];

test("semantic text pairings meet WCAG AA", () => {
  const failures = [];
  for (const [themeId, fgKey, bgKey, minimum] of textPairings) {
    const theme = themes[themeId];
    const ratio = contrastRatio(theme[fgKey], theme[bgKey]);
    if (ratio < minimum) {
      failures.push(
        `${themeId} ${fgKey} on ${bgKey}: ${ratio.toFixed(2)} (need ${minimum})`,
      );
    }
  }
  assert.deepEqual(failures, []);
});

test("tier glyphs meet 3:1 after per-theme lightness adjustment", () => {
  const failures = [];
  for (const [themeId, bgKey] of tierPairings) {
    const background = themes[themeId][bgKey];
    for (const [name, hex] of Object.entries(themeTiers[themeId])) {
      const ratio = contrastRatio(hex, background);
      if (ratio < 3) {
        failures.push(`${name} on ${themeId} ${bgKey}: ${ratio.toFixed(2)}`);
      }
    }
  }
  assert.deepEqual(failures, []);
});
