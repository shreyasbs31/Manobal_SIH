import { Redirect, Tabs } from "expo-router";

import { personnelCopy } from "../../src/copy";
import { useSession } from "../session-context";
import { colors } from "../theme";

export default function AppTabs() {
  const { ready, session } = useSession();
  const copy = personnelCopy("en");

  if (ready && !session) {
    return <Redirect href="/" />;
  }

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.paper },
        headerShadowVisible: false,
        headerTitleStyle: { color: colors.ink, fontWeight: "600" },
        tabBarActiveTintColor: colors.steady,
        tabBarInactiveTintColor: colors.inkSoft,
        tabBarStyle: {
          backgroundColor: colors.raised,
          minHeight: 64,
          borderTopColor: colors.rule,
        },
        tabBarLabelStyle: { fontSize: 12, fontWeight: "600" },
      }}
    >
      <Tabs.Screen name="index" options={{ title: copy.today }} />
      <Tabs.Screen name="checkin" options={{ title: copy.checkin }} />
      <Tabs.Screen name="talk" options={{ title: copy.talk }} />
      <Tabs.Screen name="more" options={{ title: copy.more }} />
    </Tabs>
  );
}
