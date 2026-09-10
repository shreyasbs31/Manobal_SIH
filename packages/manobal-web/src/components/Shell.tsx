import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import type { Session } from "../api/types";
import { clearSession, homeFor } from "../auth/session";
import { roleLabel, shortToken } from "../ui/format";

type Props = {
  session: Session;
  children: ReactNode;
};

export function Shell({ session, children }: Props) {
  const links = linksFor(session.role);
  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="rail">
        <div>
          <div className="brand">MANOBAL</div>
          <div className="zone">Zone 2 · analytics</div>
        </div>
        <nav aria-label="Console">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === homeFor(session.role)}>
              {link.label}
            </NavLink>
          ))}
          {session.role === "personnel"
            ? PERSONNEL_JUMPS.map((link) => (
                <a key={link.href} href={link.href}>
                  {link.label}
                </a>
              ))
            : null}
        </nav>
        <div className="who">
          <strong>{roleLabel(session.role)}</strong>
          {session.unitCode}
          <br />
          {session.actorId.length > 18 ? shortToken(session.actorId) : session.actorId}
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
        </div>
      </aside>
      <main className="main" id="main">
        {children}
      </main>
    </div>
  );
}

const PERSONNEL_JUMPS = [
  { href: "#journal", label: "Journal" },
  { href: "#instruments", label: "Questionnaires" },
  { href: "#flags", label: "Flags" },
  { href: "#devices", label: "Devices" },
];

function linksFor(role: Session["role"]): { to: string; label: string }[] {
  if (role === "personnel") {
    return [{ to: "/me", label: "My record" }];
  }
  if (role === "welfare_officer") {
    return [{ to: "/officer", label: "Case queue" }];
  }
  if (role === "medical_officer") {
    return [{ to: "/clinical", label: "Clinical" }];
  }
  if (role === "commander") {
    return [{ to: "/commander", label: "Unit picture" }];
  }
  return [
    { to: "/wdec", label: "Oversight" },
    { to: "/clinical", label: "Rulesets" },
  ];
}
