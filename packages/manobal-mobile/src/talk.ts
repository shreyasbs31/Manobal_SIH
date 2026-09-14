import type { AgentTurn } from "./api/types";
import { triage } from "./triage";

export type TalkIntent =
  | { kind: "empty" }
  | { kind: "crisis"; message: string; holdOnDevice: true }
  | { kind: "send"; message: string };

export function prepareTalk(message: string): TalkIntent {
  const trimmed = message.trim();
  if (!trimmed) {
    return { kind: "empty" };
  }
  if (triage(trimmed).crisis) {
    return { kind: "crisis", message: trimmed, holdOnDevice: true };
  }
  return { kind: "send", message: trimmed };
}

export function crisisNotice(): AgentTurn {
  return {
    session_id: "on-device",
    reply:
      "Urgent help has been requested. Those words stayed on this device. Helplines are on More.",
    crisis: true,
    accepted: true,
  };
}
