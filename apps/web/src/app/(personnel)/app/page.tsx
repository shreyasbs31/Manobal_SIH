import {
  BaselineRibbonChart,
  DomainChip,
} from "@manobal/ui";
import Link from "next/link";

const ribbon = [
  { day: 1, value: 3.2 },
  { day: 10, value: 3.0 },
  { day: 20, value: 3.1 },
  { day: 30, value: 3.4 },
  { day: 40, value: 4.6 },
  { day: 50, value: 5.2 },
  { day: 60, value: 5.8 },
] as const;

export default function SaathiHomePage() {
  return (
    <div className="mb-home-stack">
      <h1>Good morning</h1>
      <p>You have been on duty 11 days in a row. A short recovery routine can help.</p>
      <article className="mb-card">
        <h2>Today&apos;s check-in</h2>
        <p>Three taps. Mood, energy, sleep. Under 20 seconds.</p>
        <Link className="mb-primary" href="/app/saathi">
          Talk to Saathi
        </Link>
      </article>
      <BaselineRibbonChart label="Your mood against your usual range" values={ribbon} />
      <article className="mb-card">
        <h2>Why am I seeing this?</h2>
        <p>Roster days are running long this rotation. This is a private nudge.</p>
        <div className="mb-action-row">
          <DomainChip label="Roster" />
          <DomainChip label="Sleep" />
        </div>
      </article>
      <div className="mb-action-row">
        <Link className="mb-secondary" href="/app/saathi">
          Talk to Saathi
        </Link>
        <Link className="mb-secondary" href="/app/toolkit">
          Breathe 2 minutes
        </Link>
        <Link className="mb-secondary" href="/app/me">
          Plan my leave
        </Link>
      </div>
    </div>
  );
}
