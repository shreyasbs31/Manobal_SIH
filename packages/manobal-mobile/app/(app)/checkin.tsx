import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { ApiError } from "../../src/api/client";
import { personnelCopy } from "../../src/copy";
import { useApi } from "../use-api";
import { styles } from "../theme";

const FIELDS = [
  ["mood", "Mood", ["Very low", "Low", "Okay", "Good", "Strong"]],
  ["sleep_quality", "Sleep", ["Broken", "Thin", "Fair", "Solid", "Rested"]],
  ["stress", "Stress", ["Calm", "Mild", "Steady", "High", "Wired"]],
  ["fatigue", "Fatigue", ["Fresh", "Tired", "Worn", "Heavy", "Spent"]],
  ["connection", "Connection", ["Alone", "Distant", "Some", "Close", "Held"]],
] as const;

type Field = (typeof FIELDS)[number][0];

const INITIAL: Record<Field, number> = {
  mood: 3,
  sleep_quality: 3,
  stress: 3,
  fatigue: 3,
  connection: 3,
};

export default function CheckinScreen() {
  const api = useApi();
  const copy = personnelCopy("en");
  const [values, setValues] = useState(INITIAL);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [pictureNote, setPictureNote] = useState("");

  useEffect(() => {
    void api
      .checkin()
      .then((row) => {
        setValues({
          mood: row.mood ?? 3,
          sleep_quality: row.sleep_quality ?? 3,
          stress: row.stress ?? 3,
          fatigue: row.fatigue ?? 3,
          connection: row.connection ?? 3,
        });
      })
      .catch(() => {
        /* first visit has no row */
      });
  }, [api]);

  async function save() {
    setError("");
    setSaved("");
    setPictureNote("");
    try {
      const row = await api.submitCheckin(values);
      setSaved(copy.saved);
      if (row.picture_changed && row.tier && row.previous_tier) {
        setPictureNote(`${copy.pictureMoved} ${row.previous_tier} → ${row.tier}.`);
      } else if (row.picture_changed && row.tier) {
        setPictureNote(`${copy.pictureMoved} ${row.tier}.`);
      } else {
        setPictureNote(copy.pictureSame);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "could not save the check-in");
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={styles.brass} />
      <Text style={styles.title}>{copy.checkin}</Text>
      <Text style={styles.lede}>{copy.checkinHint}</Text>
      {error ? (
        <View style={[styles.notice, styles.noticeError]} accessibilityRole="alert">
          <Text style={styles.body}>{error}</Text>
        </View>
      ) : null}
      {saved ? (
        <View style={styles.notice}>
          <Text style={styles.body}>{saved}</Text>
          {pictureNote ? <Text style={[styles.muted, { marginTop: 6 }]}>{pictureNote}</Text> : null}
        </View>
      ) : null}
      {FIELDS.map(([field, label, words]) => {
        const value = values[field];
        return (
          <View key={field} style={styles.panel}>
            <Text style={styles.heading}>{label}</Text>
            <Text style={styles.muted}>{words[value - 1] ?? ""}</Text>
            <View style={styles.row}>
              {[1, 2, 3, 4, 5].map((score) => {
                const on = value === score;
                return (
                  <Pressable
                    key={score}
                    accessibilityRole="button"
                    accessibilityLabel={`${label} ${score}, ${words[score - 1] ?? ""}`}
                    accessibilityState={{ selected: on }}
                    onPress={() => setValues((current) => ({ ...current, [field]: score }))}
                    style={[styles.chip, on ? styles.chipOn : null]}
                  >
                    <Text style={[styles.chipText, on ? styles.chipTextOn : null]}>{score}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        );
      })}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Save check-in"
        onPress={() => void save()}
        style={styles.button}
      >
        <Text style={styles.buttonText}>Save</Text>
      </Pressable>
    </ScrollView>
  );
}
