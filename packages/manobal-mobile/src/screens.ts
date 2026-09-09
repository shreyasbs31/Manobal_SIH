/** Lock-screen copy is a public surface in a barracks (FR-6.2). */

export const LOCK_SCREEN_BODY = "MANOBAL: 1 welfare item needs your review.";
export const LOCK_SCREEN_URGENT = "MANOBAL: 1 urgent welfare item needs your review.";

export type Screen =
  | "consent"
  | "checkin"
  | "sos"
  | "agent"
  | "journal"
  | "assessment";

export const SCREENS: Record<Screen, { title: string; collects: string }> = {
  consent: { title: "What you share", collects: "independent grants, never accept-all" },
  checkin: { title: "Today", collects: "four 1-5 items, no free text" },
  sos: { title: "Need help now", collects: "accepted flag only" },
  agent: { title: "Talk", collects: "ephemeral turn; crisis never reaches a model" },
  journal: { title: "Journal", collects: "ciphertext on device until sync; never scored" },
  assessment: { title: "Your picture", collects: "tier and category names only" },
};

export function lockScreenBody(urgent: boolean): string {
  return urgent ? LOCK_SCREEN_URGENT : LOCK_SCREEN_BODY;
}
