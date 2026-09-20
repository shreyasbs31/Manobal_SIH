const TITLES: Record<string, string> = {
  pss10: "How you've been feeling",
  who5: "How you've been lately",
  cbi: "Tiredness from work",
  phq9: "Mood and energy",
  gad7: "Worry",
  pcptsd5: "After a hard event",
  auditc: "Alcohol, private",
};

export function assessmentTitle(id: string, fallback?: string): string {
  return TITLES[id] ?? fallback ?? "Assessment";
}
