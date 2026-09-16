import { arjunHome } from "@manobal/contracts";
import {
  BaselineRibbonChart,
  ContourTexture,
  IconLeaveWindow,
  IconShiftMoon,
  IconVoiceContour,
} from "@manobal/ui";
import { SceneSleepWindDown } from "@manobal/illustrations";
import Link from "next/link";

export default function SaathiHomePage() {
  return (
    <div className="mb-home-stack">
      <div className="mb-ribbon-hero">
        <ContourTexture height={180} seed={arjunHome.persona_id} width={390} />
        <BaselineRibbonChart
          label="Your mood and sleep against your usual range"
          takeaway={arjunHome.takeaway}
          values={arjunHome.ribbon}
          variant="hero"
        />
      </div>
      <article className="mb-checkin-card">
        <div>
          <h2>{arjunHome.checkin.title}</h2>
          <p>{arjunHome.checkin.duration_s} seconds</p>
        </div>
        <Link className="mb-primary" href={arjunHome.checkin.href}>
          Start
        </Link>
      </article>
      <p className="mb-section-label">For you now</p>
      <article className="mb-context-card">
        <SceneSleepWindDown />
        <div>
          <h2>{arjunHome.nudge.title}</h2>
          <p>{arjunHome.nudge.detail}</p>
          <p>Why this? {arjunHome.nudge.why}</p>
        </div>
      </article>
      <nav aria-label="Shortcuts" className="mb-quick-tiles">
        <Link href="/app/saathi">
          <IconVoiceContour height={22} width={22} />
          Talk
        </Link>
        <Link href="/app/toolkit/breathe">
          <IconShiftMoon height={22} width={22} />
          Breathe
        </Link>
        <Link href="/app/saathi">
          <IconVoiceContour height={22} width={22} />
          Counsellor
        </Link>
        <Link href="/app/me">
          <IconLeaveWindow height={22} width={22} />
          Leave
        </Link>
      </nav>
    </div>
  );
}
