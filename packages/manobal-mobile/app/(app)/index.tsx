import { useCallback, useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { ApiError } from "../../src/api/client";
import type { Assessment, Insights, OwnTrends } from "../../src/api/types";
import { personnelCopy } from "../../src/copy";
import { useApi } from "../use-api";
import { TIER_CAPTION, colors, styles, tierColor } from "../theme";

const SLEEP_WORDS = ["", "Broken", "Thin", "Fair", "Solid", "Rested"] as const;

export default function TodayScreen() {
  const api = useApi();
  const router = useRouter();
  const copy = personnelCopy("en");
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [trends, setTrends] = useState<OwnTrends | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    const [nextAssessment, nextTrends, nextInsights] = await Promise.all([
      api.assessment(),
      api.trends(),
      api.insights(),
    ]);
    setAssessment(nextAssessment);
    setTrends(nextTrends);
    setInsights(nextInsights);
  }, [api]);

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "could not load your record");
    });
  }, [refresh]);

  const week = [...(trends?.checkins ?? [])].slice(0, 7).reverse();
  const tier = assessment?.tier ?? null;

  function openNext(href: string) {
    if (href === "talk") {
      router.push("/(app)/talk");
      return;
    }
    if (href === "help") {
      router.push("/(app)/more");
      return;
    }
    router.push("/(app)/checkin");
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={styles.brass} />
      <Text style={styles.eyebrow}>{copy.today}</Text>
      <Text style={styles.title}>{copy.picture}</Text>
      {error ? (
        <View style={[styles.notice, styles.noticeError]} accessibilityRole="alert">
          <Text style={styles.body}>{error}</Text>
        </View>
      ) : null}
      <View style={styles.panel}>
        <Text style={[styles.title, { color: tierColor(tier), marginBottom: 4 }]}>
          {tier ?? "—"}
        </Text>
        <Text style={styles.body}>{tier ? TIER_CAPTION[tier] ?? "Assessed" : "No picture yet"}</Text>
        {insights?.lede ? <Text style={[styles.body, { marginTop: 10 }]}>{insights.lede}</Text> : null}
        <Text style={[styles.muted, { marginTop: 8 }]}>
          {(assessment?.contributing_categories ?? []).join(" · ") || "Category names only."}
        </Text>
        {insights?.streak ? (
          <Text style={[styles.muted, { marginTop: 6 }]}>
            {copy.streak}: {insights.streak === 1 ? "1 day" : `${insights.streak} days`}
          </Text>
        ) : null}
        {assessment?.why?.length ? (
          <View style={{ marginTop: 14 }}>
            <Text style={styles.heading}>{copy.why}</Text>
            {assessment.why.map((row) => (
              <Text key={row.category} style={[styles.body, { marginBottom: 6 }]}>
                {row.meaning}
              </Text>
            ))}
          </View>
        ) : null}
        {insights?.notes.length ? (
          <View style={{ marginTop: 12 }}>
            {insights.notes.map((note) => (
              <Text key={note.field} style={[styles.body, { marginBottom: 6 }]}>
                {note.text}
              </Text>
            ))}
          </View>
        ) : null}
        {insights?.settled_low && insights.settled_message ? (
          <View style={[styles.notice, { marginTop: 12, marginBottom: 0 }]}>
            <Text style={styles.body}>{insights.settled_message}</Text>
          </View>
        ) : null}
        {insights?.engine_note ? (
          <Text style={[styles.muted, { marginTop: 12 }]}>
            {copy.engine}. {insights.engine_note}
          </Text>
        ) : null}
        {assessment?.offer_checkin ? (
          <View style={[styles.notice, { marginTop: 12, marginBottom: 0 }]}>
            <Text style={styles.body}>
              Extra check-in offered after a unit incident
              {assessment.incident_category ? ` (${assessment.incident_category})` : ""}. Optional,
              not itself a flag.
            </Text>
          </View>
        ) : null}
      </View>
      {insights?.next.length ? (
        <View style={styles.panel}>
          <Text style={styles.heading}>{copy.next}</Text>
          {insights.next.map((item) => (
            <Pressable
              key={item.id}
              accessibilityRole="button"
              accessibilityLabel={item.title}
              onPress={() => openNext(item.href)}
              style={styles.actionCard}
            >
              <Text style={styles.heading}>{item.title}</Text>
              <Text style={styles.muted}>{item.detail}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      <View style={styles.panel}>
        <Text style={styles.heading}>This week</Text>
        {week.length ? (
          <View style={[styles.row, { alignItems: "flex-end", minHeight: 92 }]}>
            {week.map((row) => {
              const sleep = row.sleep_quality ?? row.mood ?? 1;
              return (
                <View key={row.observed_on} style={{ alignItems: "center", width: 40 }}>
                  <View
                    accessibilityLabel={`${row.observed_on} sleep ${SLEEP_WORDS[sleep] ?? sleep}`}
                    style={{
                      width: 16,
                      height: 10 + sleep * 10,
                      backgroundColor: colors.rail,
                    }}
                  />
                  <Text style={[styles.muted, { fontSize: 10, marginTop: 4 }]}>
                    {row.observed_on.slice(5)}
                  </Text>
                  <Text style={[styles.muted, { fontSize: 10 }]}>{SLEEP_WORDS[sleep] ?? ""}</Text>
                </View>
              );
            })}
          </View>
        ) : (
          <Text style={styles.muted}>Save today’s check-in to start a private trend.</Text>
        )}
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={copy.checkin}
        onPress={() => router.push("/(app)/checkin")}
        style={styles.button}
      >
        <Text style={styles.buttonText}>{copy.checkin}</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Refresh"
        onPress={() => {
          setError("");
          void refresh().catch((err: unknown) => {
            setError(err instanceof ApiError ? err.message : "could not load your record");
          });
        }}
        style={[styles.button, styles.buttonGhost]}
      >
        <Text style={[styles.buttonText, styles.buttonGhostText]}>Refresh</Text>
      </Pressable>
    </ScrollView>
  );
}
