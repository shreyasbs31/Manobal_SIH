import { StyleSheet } from "react-native";

export const colors = {
  ink: "#161c18",
  inkSoft: "#4d574f",
  paper: "#f3eee3",
  raised: "#fbf8f1",
  rule: "#d4ccb8",
  signal: "#9a1f1a",
  watch: "#8a5410",
  steady: "#27583a",
  focus: "#1d4e6c",
  rail: "#1a221e",
  brass: "#c4a574",
} as const;

export const TIER_CAPTION: Record<string, string> = {
  T0: "Within your usual range",
  T1: "Visible only to you",
  T2: "A welfare conversation",
  T3: "Needs a closer look",
  T4: "Urgent support",
};

export function tierColor(tier: string | null | undefined): string {
  if (tier === "T4") {
    return colors.signal;
  }
  if (tier === "T3") {
    return colors.watch;
  }
  if (tier === "T2") {
    return colors.focus;
  }
  return colors.steady;
}

export const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.paper,
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 28,
  },
  brass: {
    width: 40,
    height: 4,
    backgroundColor: colors.brass,
    marginBottom: 14,
  },
  eyebrow: {
    color: colors.inkSoft,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    marginBottom: 6,
  },
  title: {
    color: colors.ink,
    fontSize: 30,
    fontWeight: "600",
    marginBottom: 8,
  },
  lede: {
    color: colors.inkSoft,
    fontSize: 16,
    lineHeight: 23,
    marginBottom: 16,
  },
  panel: {
    backgroundColor: colors.raised,
    borderColor: colors.rule,
    borderWidth: 1,
    borderRadius: 4,
    padding: 16,
    marginBottom: 14,
  },
  heading: {
    color: colors.ink,
    fontSize: 17,
    fontWeight: "600",
    marginBottom: 8,
  },
  body: {
    color: colors.ink,
    fontSize: 16,
    lineHeight: 23,
  },
  muted: {
    color: colors.inkSoft,
    fontSize: 14,
    lineHeight: 20,
  },
  notice: {
    backgroundColor: "#efe4c8",
    borderRadius: 4,
    padding: 12,
    marginBottom: 12,
  },
  noticeError: {
    backgroundColor: "#f3d6d4",
  },
  button: {
    backgroundColor: colors.rail,
    minHeight: 52,
    borderRadius: 4,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    marginTop: 10,
  },
  buttonGhost: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.rail,
  },
  buttonDanger: {
    backgroundColor: colors.signal,
    borderColor: colors.signal,
  },
  buttonText: {
    color: colors.paper,
    fontSize: 16,
    fontWeight: "600",
  },
  buttonGhostText: {
    color: colors.ink,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.rule,
    backgroundColor: "#fffdf8",
    borderRadius: 4,
    minHeight: 48,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.ink,
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  chip: {
    minWidth: 44,
    minHeight: 44,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: colors.rule,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  chipOn: {
    backgroundColor: colors.rail,
    borderColor: colors.rail,
  },
  chipText: {
    color: colors.ink,
    fontSize: 16,
    fontWeight: "500",
  },
  chipTextOn: {
    color: colors.paper,
    fontWeight: "700",
  },
  actionCard: {
    borderWidth: 1,
    borderColor: colors.rule,
    backgroundColor: colors.paper,
    borderRadius: 4,
    padding: 12,
    marginTop: 10,
    minHeight: 64,
  },
  bubbleYou: {
    alignSelf: "flex-end",
    backgroundColor: "#e8d7b5",
    borderLeftWidth: 3,
    borderLeftColor: colors.brass,
    maxWidth: "88%",
    padding: 12,
    marginBottom: 8,
  },
  bubbleThem: {
    alignSelf: "flex-start",
    backgroundColor: colors.raised,
    borderWidth: 1,
    borderColor: colors.rule,
    maxWidth: "88%",
    padding: 12,
    marginBottom: 8,
  },
  mic: {
    minHeight: 72,
    borderRadius: 4,
    backgroundColor: colors.rail,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 12,
  },
  micHot: {
    backgroundColor: colors.signal,
  },
});
