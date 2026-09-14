import { Component, useMemo, useState, type ReactNode } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { ApiError } from "../../src/api/client";
import { asChatLine, linesAfterCrisis, type ChatLine } from "../../src/conversation";
import { personnelCopy } from "../../src/copy";
import { prepareTalk } from "../../src/talk";
import { useApi } from "../use-api";
import { styles } from "../theme";

class VoiceBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <Text style={styles.muted}>Type below. Voice is not available in this Expo Go build.</Text>
      );
    }
    return this.props.children;
  }
}

function loadHoldToTalk() {
  try {
    return require("../../src/hold-to-talk").HoldToTalk as typeof import("../../src/hold-to-talk").HoldToTalk;
  } catch {
    return null;
  }
}

export default function TalkScreen() {
  const api = useApi();
  const copy = personnelCopy("en");
  const HoldToTalk = useMemo(() => loadHoldToTalk(), []);
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function deliver(text: string) {
    const next = prepareTalk(text);
    if (next.kind === "empty") {
      return;
    }
    if (next.kind === "crisis") {
      setLines((current) => linesAfterCrisis(current, next.message));
      setDraft("");
      setError("");
      try {
        await api.sos();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "could not send SOS");
      }
      return;
    }
    setBusy(true);
    setError("");
    setLines((current) => [...current, asChatLine("you", next.message, false, `${current.length}-you`)]);
    setDraft("");
    try {
      const turn = await api.agent(next.message, sessionId || undefined);
      setSessionId(turn.session_id);
      setLines((current) => [
        ...current,
        asChatLine("listener", turn.reply, turn.crisis, `${current.length}-listener`),
      ]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "could not send the message");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ paddingBottom: 48 }}>
      <View style={styles.brass} />
      <Text style={styles.title}>{copy.talk}</Text>
      <Text style={styles.lede}>{copy.talkHint}</Text>
      {error ? (
        <View style={[styles.notice, styles.noticeError]} accessibilityRole="alert">
          <Text style={styles.body}>{error}</Text>
        </View>
      ) : null}
      <View style={styles.panel} accessibilityLiveRegion="polite">
        {lines.length ? (
          lines.map((line) => (
            <View
              key={line.id}
              style={line.role === "you" ? styles.bubbleYou : styles.bubbleThem}
            >
              <Text style={styles.muted}>{line.role === "you" ? "You" : "Listener"}</Text>
              <Text style={styles.body}>{line.text}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.muted}>Hold the button and speak. This is not scored.</Text>
        )}
        {busy ? <Text style={styles.muted}>{copy.thinking}</Text> : null}
      </View>
      {HoldToTalk ? (
        <VoiceBoundary>
          <HoldToTalk
            idleLabel={copy.holdToTalk}
            listeningLabel={copy.listening}
            transcribe={api.transcribe}
            onTranscript={(text) => void deliver(text)}
            onError={setError}
          />
        </VoiceBoundary>
      ) : (
        <Text style={styles.muted}>Type your message. Voice needs a microphone on this device.</Text>
      )}
      <Text nativeID="talk-message-label" style={[styles.heading, { marginTop: 16 }]}>
        Or type
      </Text>
      <TextInput
        accessibilityLabelledBy="talk-message-label"
        accessibilityLabel="Message"
        value={draft}
        onChangeText={setDraft}
        multiline
        style={[styles.input, { minHeight: 88, textAlignVertical: "top" }]}
      />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={copy.send}
        accessibilityState={{ disabled: busy }}
        disabled={busy}
        onPress={() => void deliver(draft)}
        style={styles.button}
      >
        <Text style={styles.buttonText}>{busy ? copy.thinking : copy.send}</Text>
      </Pressable>
    </ScrollView>
  );
}
