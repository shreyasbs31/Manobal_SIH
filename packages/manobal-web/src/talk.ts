export type TalkIntent =
  | { kind: "empty" }
  | { kind: "crisis"; message: string; holdOnDevice: true }
  | { kind: "send"; message: string };

export type ChatLine = {
  id: string;
  role: "you" | "listener";
  text: string;
  crisis?: boolean;
};

const CRISIS = /\b(kill myself|end my life|want to die|suicid)/i;

export function prepareTalk(message: string): TalkIntent {
  const trimmed = message.trim();
  if (!trimmed) {
    return { kind: "empty" };
  }
  if (CRISIS.test(trimmed)) {
    return { kind: "crisis", message: trimmed, holdOnDevice: true };
  }
  return { kind: "send", message: trimmed };
}

export function crisisNotice(): string {
  return "Urgent help has been requested. Those words stayed on this desk. Helplines are under Help.";
}

export function appendYou(current: ChatLine[], spoken: string, crisis = false): ChatLine[] {
  return [...current, { id: `${current.length}-you`, role: "you", text: spoken, crisis }];
}

export function appendListener(current: ChatLine[], reply: string, crisis = false): ChatLine[] {
  return [...current, { id: `${current.length}-listener`, role: "listener", text: reply, crisis }];
}
