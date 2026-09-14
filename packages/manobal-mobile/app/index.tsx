import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Redirect, useRouter } from "expo-router";

import { ApiError, mintPersonnelToken, publicHeaders } from "../src/api/client";
import { personnelCopy } from "../src/copy";
import { defaultApiUrl } from "./config";
import { useSession } from "./session-context";
import { styles } from "./theme";

export default function PairScreen() {
  const router = useRouter();
  const { session, ready, enter } = useSession();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const copy = personnelCopy("en");

  if (ready && session) {
    return <Redirect href="/(app)" />;
  }

  async function pair() {
    setBusy(true);
    setError("");
    try {
      const baseUrl = defaultApiUrl();
      const seedResponse = await fetch(`${baseUrl}/dev/seed`, { headers: publicHeaders() });
      const seed = (await seedResponse.json()) as { personnel_token?: string; unit_code?: string };
      if (!seedResponse.ok || !seed.personnel_token) {
        throw new ApiError(seedResponse.status, "MB-5000", "demo seed is not available");
      }
      const token = await mintPersonnelToken({
        baseUrl,
        subjectToken: seed.personnel_token,
        unitCode: seed.unit_code || "12BN_A",
      });
      await enter({
        token,
        subjectToken: seed.personnel_token,
        unitCode: seed.unit_code || "12BN_A",
      });
      router.replace("/(app)");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "could not reach the unit server");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.screen}>
      <View style={{ height: 56 }} />
      <View style={styles.brass} />
      <Text style={styles.eyebrow}>Uniformed welfare</Text>
      <Text style={styles.title}>{copy.title}</Text>
      <Text style={styles.lede}>{copy.lede}</Text>
      <View style={styles.panel}>
        <Text style={styles.body}>This phone holds a subject token, never a service number.</Text>
        <Text style={[styles.muted, { marginTop: 8 }]}>
          Speak on Talk. The unit server transcribes. Crisis words never reach a model.
        </Text>
      </View>
      {error ? (
        <View style={[styles.notice, styles.noticeError]} accessibilityRole="alert">
          <Text style={styles.body}>{error}</Text>
        </View>
      ) : null}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={copy.enter}
        accessibilityState={{ disabled: busy, busy }}
        disabled={busy}
        onPress={() => void pair()}
        style={styles.button}
      >
        <Text style={styles.buttonText}>{busy ? "Pairing…" : copy.enter}</Text>
      </Pressable>
    </View>
  );
}
