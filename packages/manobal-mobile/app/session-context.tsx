import { createContext, useContext, type ReactNode } from "react";

import type { MobileSession } from "../src/session";

type SessionApi = {
  session: MobileSession | null;
  ready: boolean;
  enter: (next: MobileSession) => Promise<void>;
  leave: () => Promise<void>;
};

const SessionContext = createContext<SessionApi | null>(null);

export function SessionProvider({
  value,
  children,
}: {
  value: SessionApi;
  children: ReactNode;
}) {
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionApi {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return value;
}
