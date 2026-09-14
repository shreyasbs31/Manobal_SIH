import Constants from "expo-constants";
import { Platform } from "react-native";

function lanHost(): string {
  const go = Constants.expoGoConfig as { debuggerHost?: string } | null;
  const candidates = [
    process.env.EXPO_PUBLIC_API_HOST,
    Constants.expoConfig?.hostUri,
    go?.debuggerHost,
    Constants.linkingUri,
  ];
  for (const raw of candidates) {
    if (typeof raw !== "string" || !raw.trim()) {
      continue;
    }
    const host = raw
      .replace(/^\w+:\/\//, "")
      .split("/")[0]
      ?.split(":")[0];
    if (host && host !== "localhost" && host !== "127.0.0.1") {
      return host;
    }
  }
  return "";
}

export function defaultApiUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }
  const extra = Constants.expoConfig?.extra?.apiUrl;
  if (typeof extra === "string" && extra.trim()) {
    return extra.replace(/\/$/, "");
  }
  const host = lanHost();
  if (host) {
    return `http://${host}:8000`;
  }
  if (Platform.OS === "android") {
    return "http://10.0.2.2:8000";
  }
  return "http://127.0.0.1:8000";
}
