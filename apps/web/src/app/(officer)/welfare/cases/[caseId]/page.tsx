import { arjunWorkspace, PERSONA_IDS, welfareQueue } from "@manobal/contracts";
import {
  BriefPanel,
  CaseStrip,
  EscalationLadder,
  LeverOption,
  SlaTimer,
  TierBadge,
  TrajectoryArrow,
} from "@manobal/ui";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function CaseWorkspacePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  if (!(PERSONA_IDS as readonly string[]).includes(caseId)) {
    notFound();
  }
  const item = welfareQueue.find((entry) => entry.case_id === caseId) ?? arjunWorkspace.case;
  const workspace = caseId === "MB-4091" ? arjunWorkspace : { ...arjunWorkspace, case: item };

  return (
    <div className="mb-case-work">
      <header className="mb-action-row">
        <Link className="mb-ghost" href="/welfare">
          Queue
        </Link>
        <strong>{item.case_id}</strong>
        <TierBadge tier={item.tier} />
        <TrajectoryArrow direction={item.trajectory} />
        <SlaTimer
          label="SLA"
          remainingLabel={item.sla_label}
          remainingRatio={item.remaining_ratio}
          tier={item.tier}
        />
      </header>
      <CaseStrip
        actions={workspace.actions}
        days={workspace.strip}
        incidents={workspace.incidents}
        onsetDay={workspace.onset_day}
      />
      <div className="mb-case-cols">
        <section>
          <h2>What changed</h2>
          {workspace.what_changed.map((row) => (
            <p key={row.title}>
              <strong>{row.title}</strong>
              <br />
              {row.detail}
            </p>
          ))}
          <p>Trend sharing: Sleep, request pending.</p>
        </section>
        <section>
          <h2>Recommended actions</h2>
          {workspace.levers.map((lever, index) => (
            <LeverOption
              hint={lever.hint}
              index={index + 1}
              key={lever.title}
              rationale={lever.rationale}
              title={lever.title}
            />
          ))}
          <BriefPanel>
            <p lang="hi">{workspace.brief}</p>
          </BriefPanel>
        </section>
        <section>
          <h2>Identity</h2>
          <p>Locked</p>
          <button className="mb-secondary" type="button">
            Reveal to contact
          </button>
          <p>This person will see that you viewed it.</p>
          <h2>Log</h2>
          <EscalationLadder
            current="waiting"
            steps={[
              { role: "UWO", status: "acknowledged", time: "09:12" },
              { role: "Company welfare deputy", status: "notified", time: "09:18" },
              { role: "Battalion MO", status: "waiting", time: "" },
              { role: "Sector counsellor", status: "waiting", time: "" },
            ]}
          />
          <button className="mb-secondary" type="button">
            Close case
          </button>
        </section>
      </div>
    </div>
  );
}
