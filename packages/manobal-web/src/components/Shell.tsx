import { NavLink } from "react-router-dom";

import type { Session } from "../api/types";
import { clearSession, homeFor } from "../auth/session";

type Props = {
  session: Session;
  children: React.ReactNode;
};

export function Shell({ session, children }: Props) {
  const links = linksFor(session.role);
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">MANOBAL</div>
        <div className="zone">Zone 2 · analytics plane</div>
        <nav aria-label="Console">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === homeFor(session.role)}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <p className="muted">
          {session.role.replace("_", " ")}
          <br />
          {session.actorId}
        </p>
        <button
          className="ghost"
          type="button"
          onClick={() => {
            clearSession();
            window.location.assign("/");
          }}
        >
          End session
        </button>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function linksFor(role: Session["role"]): { to: string; label: string }[] {
  if (role === "personnel") {
    return [{ to: "/me", label: "My record" }];
  }
  if (role === "welfare_officer" || role === "medical_officer") {
    return [
      { to: "/officer", label: "Case queue" },
      ...(role === "medical_officer" ? [{ to: "/clinical", label: "Rulesets" }] : []),
    ];
  }
  if (role === "commander") {
    return [{ to: "/commander", label: "Unit picture" }];
  }
  return [
    { to: "/wdec", label: "Oversight" },
    { to: "/clinical", label: "Rulesets" },
  ];
}
