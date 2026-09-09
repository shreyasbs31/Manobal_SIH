import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import type { Role, Session } from "./api/types";
import { homeFor, readSession } from "./auth/session";
import { Shell } from "./components/Shell";
import { Clinical } from "./pages/Clinical";
import { Commander } from "./pages/Commander";
import { Gate } from "./pages/Gate";
import { OfficerCase } from "./pages/OfficerCase";
import { OfficerQueue } from "./pages/OfficerQueue";
import { Personnel } from "./pages/Personnel";
import { Wdec } from "./pages/Wdec";

export function App() {
  const [session, setSession] = useState<Session | null>(readSession);
  const [personnelToken, setPersonnelToken] = useState("tok_seed_0000");

  useEffect(() => {
    void fetch("/dev/seed")
      .then((response) => response.json())
      .then((body: { personnel_token?: string }) => {
        if (body.personnel_token) {
          setPersonnelToken(body.personnel_token);
        }
      })
      .catch(() => {
        /* seed endpoint is local-only; the gate still works with the fallback token */
      });
  }, []);

  if (!session) {
    return <Gate subjectToken={personnelToken} onReady={() => setSession(readSession())} />;
  }

  return (
    <Shell session={session}>
      <Routes>
        <Route
          path="/me"
          element={
            <Require session={session} roles={["personnel"]}>
              <Personnel session={session} />
            </Require>
          }
        />
        <Route
          path="/officer"
          element={
            <Require session={session} roles={["welfare_officer", "medical_officer"]}>
              <OfficerQueue session={session} />
            </Require>
          }
        />
        <Route
          path="/officer/cases/:caseId"
          element={
            <Require session={session} roles={["welfare_officer", "medical_officer"]}>
              <OfficerCase session={session} />
            </Require>
          }
        />
        <Route
          path="/commander"
          element={
            <Require session={session} roles={["commander"]}>
              <Commander session={session} />
            </Require>
          }
        />
        <Route
          path="/wdec"
          element={
            <Require session={session} roles={["wdec_auditor"]}>
              <Wdec session={session} />
            </Require>
          }
        />
        <Route
          path="/clinical"
          element={
            <Require session={session} roles={["medical_officer", "wdec_auditor"]}>
              <Clinical session={session} />
            </Require>
          }
        />
        <Route path="*" element={<Navigate to={homeFor(session.role)} replace />} />
      </Routes>
    </Shell>
  );
}

function Require({
  session,
  roles,
  children,
}: {
  session: Session;
  roles: Role[];
  children: React.ReactNode;
}) {
  if (!roles.includes(session.role)) {
    return <Navigate to={homeFor(session.role)} replace />;
  }
  return children;
}
