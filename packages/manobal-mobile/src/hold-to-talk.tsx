import { useRef, useState } from "react";
import { Pressable, Text } from "react-native";
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from "expo-audio";

import type { AudioPart } from "./api/types";
import { styles } from "../app/theme";

type Props = {
  idleLabel: string;
  listeningLabel: string;
  transcribe: (part: AudioPart) => Promise<string>;
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
};

export function HoldToTalk({
  idleLabel,
  listeningLabel,
  transcribe,
  onTranscript,
  onError,
}: Props) {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [recording, setRecording] = useState(false);
  const startingRef = useRef<Promise<void> | null>(null);

  async function startRecording() {
    onError("");
    const work = (async () => {
      const permission = await requestRecordingPermissionsAsync();
      if (!permission.granted) {
        onError("Microphone permission is required to talk.");
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true);
    })();
    startingRef.current = work;
    try {
      await work;
    } catch {
      setRecording(false);
      onError("Could not start the microphone.");
    }
  }

  async function stopRecording() {
    if (startingRef.current) {
      await startingRef.current;
      startingRef.current = null;
    }
    if (!recording && !recorder.isRecording) {
      return;
    }
    setRecording(false);
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) {
        return;
      }
      const transcript = await transcribe({
        uri,
        name: "talk.m4a",
        type: "audio/m4a",
        language: "en",
      });
      if (transcript) {
        onTranscript(transcript);
      } else {
        onError("No words were heard. Try again or type.");
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : "could not transcribe");
    }
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={recording ? "Stop recording and send" : idleLabel}
      accessibilityState={{ selected: recording }}
      onPressIn={() => void startRecording()}
      onPressOut={() => void stopRecording()}
      style={[styles.mic, recording ? styles.micHot : null]}
    >
      <Text style={styles.buttonText}>{recording ? listeningLabel : idleLabel}</Text>
    </Pressable>
  );
}
