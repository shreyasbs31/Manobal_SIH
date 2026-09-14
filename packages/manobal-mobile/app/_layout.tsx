import { useEffect, useMemo, useState } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { clearSession, readSession, writeSession, type MobileSession } from "../src/session";
import { SessionProvider } from "./session-context";
import { deviceStore } from "./storage";

export default function RootLayout() {
  const [session, setSession] = useState<MobileSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    void readSession(deviceStore).then((next) => {
      if (active) {
        setSession(next);
        setReady(true);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo(
    () => ({
      session,
      ready,
      enter: async (next: MobileSession) => {
        await writeSession(deviceStore, next);
        setSession(next);
      },
      leave: async () => {
        await clearSession(deviceStore);
        setSession(null);
      },
    }),
    [ready, session],
  );

  return (
    <SessionProvider value={value}>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </SessionProvider>
  );
}
