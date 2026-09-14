import { useEffect, useState } from "react";
import { Linking, Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { ApiError } from "../../src/api/client";
import type { ConsentState, HelplineCard, JournalEntry } from "../../src/api/types";
import { personnelCopy } from "../../src/copy";
import { useSession } from "../session-context";
import { useApi } from "../use-api";
import { styles } from "../theme";

const DATA_TYPES = [
  ["org", "Duty and leave"],
  ["selfreport", "Check-ins and questionnaires"],
  ["biometric", "Heart rate and sleep"],
  ["voice_features", "Voice measurements"],
  ["journal", "Private journal"],
] as const;

export default function MoreScreen() {
  const api = useApi();
  const { leave } = useSession();
  const copy = personnelCopy("en");
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [draft, setDraft] = useState("");
  const [helpline, setHelpline] = useState<HelplineCard | null>(null);
  const [sos, setSos] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    const [nextConsent, journal] = await Promise.all([api.consent(), api.journal()]);
    setConsent(nextConsent);
    setEntries(journal.entries);
    setPaused(journal.paused);
    try {
      setHelpline(await api.helpline());
    } catch {
      /* numbers stay hidden until the next successful load */
    }
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "could not load");
    });
  }, [api]);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={styles.brass} />
      <Text style={styles.title}>{copy.more}</Text>
      {error ? (
        <View style={[styles.notice, styles.noticeError]} accessibilityRole="alert">
          <Text style={styles.body}>{error}</Text>
        </View>
      ) : null}

      <View style={styles.panel}>
        <Text style={styles.heading}>{copy.help}</Text>
        <Text style={styles.muted}>{copy.helplineHint}</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={copy.sos}
          onPress={() => {
            void api
              .sos()
              .then(() => setSos(true))
              .catch((err: unknown) => {
                setError(err instanceof ApiError ? err.message : "could not send SOS");
              });
          }}
          style={[styles.button, styles.buttonDanger]}
        >
          <Text style={styles.buttonText}>{sos ? "SOS sent" : copy.sos}</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={copy.helplines}
          onPress={() => {
            void api
              .helpline()
              .then(setHelpline)
              .catch((err: unknown) => {
                setError(err instanceof ApiError ? err.message : "could not load helplines");
              });
          }}
          style={[styles.button, styles.buttonGhost]}
        >
          <Text style={[styles.buttonText, styles.buttonGhostText]}>{copy.helplines}</Text>
        </Pressable>
        {helpline
          ? Object.entries(helpline.helplines).map(([name, number]) =>
              number ? (
                <Pressable
                  key={name}
                  accessibilityRole="link"
                  accessibilityLabel={`Call ${name.replaceAll("_", " ")} ${number}`}
                  onPress={() => void Linking.openURL(`tel:${number}`)}
                  style={{ marginTop: 12 }}
                >
                  <Text style={styles.body}>
                    {name.replaceAll("_", " ")} · {number}
                  </Text>
                </Pressable>
              ) : null,
            )
          : null}
        {helpline ? <Text style={[styles.muted, { marginTop: 8 }]}>Recorded: {String(helpline.recorded)}</Text> : null}
      </View>

      <View style={styles.panel}>
        <Text style={styles.heading}>{copy.consent}</Text>
        <Text style={styles.muted}>Each type is independent. There is no accept-all.</Text>
        {DATA_TYPES.map(([code, label]) => {
          const granted = consent?.consents[code];
          const state = granted === true ? "granted" : granted === false ? "withdrawn" : "unset";
          return (
            <View key={code} style={{ marginTop: 14 }}>
              <Text style={styles.body}>{label}</Text>
              <Text style={styles.muted}>{state}</Text>
              <View style={styles.row}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Grant ${label}`}
                  accessibilityState={{ selected: granted === true }}
                  onPress={() => {
                    void api
                      .setConsent(code, true)
                      .then(() => refresh())
                      .catch((err: unknown) => {
                        setError(err instanceof ApiError ? err.message : "could not update consent");
                      });
                  }}
                  style={[styles.chip, granted === true ? styles.chipOn : null]}
                >
                  <Text style={[styles.chipText, granted === true ? styles.chipTextOn : null]}>
                    Grant
                  </Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Withdraw ${label}`}
                  accessibilityState={{ selected: granted === false }}
                  onPress={() => {
                    void api
                      .setConsent(code, false)
                      .then(() => refresh())
                      .catch((err: unknown) => {
                        setError(err instanceof ApiError ? err.message : "could not update consent");
                      });
                  }}
                  style={[styles.chip, granted === false ? styles.chipOn : null]}
                >
                  <Text style={[styles.chipText, granted === false ? styles.chipTextOn : null]}>
                    Withdraw
                  </Text>
                </Pressable>
              </View>
            </View>
          );
        })}
      </View>

      <View style={styles.panel}>
        <Text style={styles.heading}>{copy.journal}</Text>
        {paused ? <Text style={styles.muted}>Journal is paused at the current tier.</Text> : null}
        <TextInput
          accessibilityLabel="Journal entry"
          value={draft}
          onChangeText={setDraft}
          multiline
          style={[styles.input, { minHeight: 88, textAlignVertical: "top" }]}
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Save journal entry"
          onPress={() => {
            void api
              .writeJournal(draft)
              .then(() => {
                setDraft("");
                return refresh();
              })
              .catch((err: unknown) => {
                setError(err instanceof ApiError ? err.message : "could not write");
              });
          }}
          style={[styles.button, styles.buttonGhost]}
        >
          <Text style={[styles.buttonText, styles.buttonGhostText]}>Save entry</Text>
        </Pressable>
        {entries.slice(0, 8).map((row) => (
          <Text key={row.id} style={[styles.muted, { marginTop: 10 }]}>
            {row.body}
          </Text>
        ))}
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={copy.signOut}
        onPress={() => void leave()}
        style={[styles.button, styles.buttonGhost]}
      >
        <Text style={[styles.buttonText, styles.buttonGhostText]}>{copy.signOut}</Text>
      </Pressable>
    </ScrollView>
  );
}
