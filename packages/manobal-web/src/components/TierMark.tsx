type Props = {
  tier: string | null | undefined;
};

const CAPTION: Record<string, string> = {
  T0: "Within your usual range",
  T1: "Visible only to you",
  T2: "A welfare conversation",
  T3: "Needs a closer look",
  T4: "Urgent support",
};

export function TierMark({ tier }: Props) {
  if (!tier) {
    return (
      <div className="tier-mark">
        <span className="tier-code muted">—</span>
        <span className="tier-caption">No assessment yet</span>
      </div>
    );
  }
  return (
    <div className={`tier-mark ${tier}`}>
      <span className="tier-code">{tier}</span>
      <span className="tier-caption">{CAPTION[tier] ?? "Assessed"}</span>
    </div>
  );
}
