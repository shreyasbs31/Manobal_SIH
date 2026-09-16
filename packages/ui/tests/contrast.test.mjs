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
    bg: "#F4F8F6",
    surface: "#FFFFFF",
    text: "#1B2427",
    muted: "#3D4F48",
    primary: "#2F5D50",
    onPrimary: "#FFFFFF",
    focus: "#2F5D50",
    sos: "#B83A2E",
    onSos: "#FFFFFF",
  },
  "saathi-dark": {
    bg: "#12211C",
    surface: "#1F4238",
    text: "#E8ECE9",
    muted: "#B7C9C1",
    primary: "#8FBEAD",
    onPrimary: "#12211C",
    focus: "#E2C56C",
    sos: "#E06A5C",
    onSos: "#140706",
  },
  "saathi-hc": {
    bg: "#FFFFFF",
    surface: "#FFFFFF",
    text: "#0B0D0E",
    muted: "#1B2427",
    primary: "#1F4238",
    onPrimary: "#FFFFFF",
    focus: "#0B0D0E",
    sos: "#8E241C",
    onSos: "#FFFFFF",
  },
  "command-dark": {
    bg: "#131C24",
    surface: "#1B2630",
    text: "#E8ECE9",
    muted: "#BFB28A",
    primary: "#C8A24A",
    onPrimary: "#131C24",
    focus: "#C8A24A",
    sos: "#B83A2E",
    onSos: "#FFFFFF",
  },
  "command-light": {
    bg: "#EEF1EB",
    surface: "#F8FAF6",
    text: "#1B2427",
    muted: "#3E4A3F",
    primary: "#8F6F1E",
    onPrimary: "#FFFFFF",
    focus: "#8F6F1E",
    sos: "#B83A2E",
    onSos: "#FFFFFF",
  },
};

const themeTiers = {
  "saathi-light": {
    t0: "#6E927F",
    t1: "#4D8BAE",
    t2: "#9A6F12",
    t3: "#D06A34",
    t4: "#B83A2E",
  },
  "saathi-dark": {
    t0: "#6E927F",
    t1: "#62A4C4",
    t2: "#D6A13D",
    t3: "#D06A34",
    t4: "#E06A5C",
  },
  "saathi-hc": {
    t0: "#3F6B5C",
    t1: "#2F6A8C",
    t2: "#9A6F12",
    t3: "#A84A1C",
    t4: "#8E241C",
  },
  "command-dark": {
    t0: "#6E927F",
    t1: "#4D8BAE",
    t2: "#D6A13D",
    t3: "#D06A34",
    t4: "#E06A5C",
  },
  "command-light": {
    t0: "#6E927F",
    t1: "#4D8BAE",
    t2: "#9A6F12",
    t3: "#D06A34",
    t4: "#B83A2E",
  },
};

test("every theme text pairing meets 4.5:1", () => {
  const failures = [];
  for (const [themeId, theme] of Object.entries(themes)) {
    const checks = [
      ["text", "bg"],
      ["text", "surface"],
      ["muted", "bg"],
      ["muted", "surface"],
      ["onPrimary", "primary"],
      ["onSos", "sos"],
    ];
    for (const [fg, bg] of checks) {
      const ratio = contrastRatio(theme[fg], theme[bg]);
      if (ratio < 4.5) {
        failures.push(
          `${themeId} ${fg} on ${bg}: ${ratio.toFixed(2)} (need 4.5)`,
        );
      }
    }
  }
  assert.deepEqual(failures, []);
});

test("every theme glyph and focus pairing meets 3:1", () => {
  const failures = [];
  for (const [themeId, theme] of Object.entries(themes)) {
    for (const [fg, bg] of [
      ["focus", "bg"],
      ["primary", "bg"],
    ]) {
      const ratio = contrastRatio(theme[fg], theme[bg]);
      if (ratio < 3) {
        failures.push(
          `${themeId} ${fg} on ${bg}: ${ratio.toFixed(2)} (need 3)`,
        );
      }
    }
    for (const [name, hex] of Object.entries(themeTiers[themeId])) {
      for (const bgKey of ["bg", "surface"]) {
        const ratio = contrastRatio(hex, theme[bgKey]);
        if (ratio < 3) {
          failures.push(
            `${themeId} ${name} on ${bgKey}: ${ratio.toFixed(2)} (need 3)`,
          );
        }
      }
    }
  }
  assert.deepEqual(failures, []);
});

test("survey paper is the command light theme", () => {
  assert.equal(themes["command-light"].bg, "#EEF1EB");
  assert.equal(themes["command-light"].surface, "#F8FAF6");
  assert.equal(themes["command-light"].primary, "#8F6F1E");
});
