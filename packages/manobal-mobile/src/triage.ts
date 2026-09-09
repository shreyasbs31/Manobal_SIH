const CRISIS_MARKERS = ["kill myself", "end my life", "want to die", "suicid"];

export function triage(message: string): { crisis: boolean; holdOnDevice: boolean } {
  const text = message.toLowerCase();
  const crisis = CRISIS_MARKERS.some((marker) => text.includes(marker));
  return { crisis, holdOnDevice: crisis };
}
