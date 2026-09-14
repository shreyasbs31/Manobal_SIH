import type { AgentTurn } from "./api/types";
import { crisisNotice, prepareTalk, type TalkIntent } from "./talk";

export type ChatLine = {
  id: string;
  role: "you" | "listener";
  text: string;
  crisis?: boolean;
};

export function asChatLine(
  role: ChatLine["role"],
  text: string,
  crisis = false,
  id = `${role}-${text.length}`,
): ChatLine {
  return { id, role, text, crisis };
}

export function intentFromVoice(transcript: string): TalkIntent {
  return prepareTalk(transcript);
}

export function linesAfterSend(
  current: ChatLine[],
  spoken: string,
  turn: AgentTurn,
): ChatLine[] {
  const n = current.length;
  return [
    ...current,
    asChatLine("you", spoken, false, `${n}-you`),
    asChatLine("listener", turn.reply, turn.crisis, `${n}-listener`),
  ];
}

export function linesAfterCrisis(current: ChatLine[], spoken: string): ChatLine[] {
  const notice = crisisNotice();
  const n = current.length;
  return [
    ...current,
    asChatLine("you", spoken, true, `${n}-you`),
    asChatLine("listener", notice.reply, true, `${n}-listener`),
  ];
}
