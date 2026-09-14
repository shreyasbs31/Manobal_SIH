import { describe, expect, it } from "vitest";

import { linesAfterCrisis, linesAfterSend } from "../src/conversation";
import { crisisNotice, prepareTalk } from "../src/talk";
import { createPersonnelClient } from "../src/api/client";

describe("talk flow", () => {
  it("holds crisis language on the device before any model turn", () => {
    const next = prepareTalk("I want to die");
    expect(next.kind).toBe("crisis");
    expect(next.kind === "crisis" && next.holdOnDevice).toBe(true);
  });

  it("sends ordinary words after trim", () => {
    const next = prepareTalk("  I have not been sleeping well  ");
    expect(next).toEqual({ kind: "send", message: "I have not been sleeping well" });
  });

  it("ignores an empty utterance", () => {
    expect(prepareTalk("   ").kind).toBe("empty");
  });

  it("keeps the crisis reply local and never names a score", () => {
    const notice = crisisNotice();
    expect(notice.crisis).toBe(true);
    expect(notice.session_id).toBe("on-device");
    expect(notice.reply).not.toMatch(/WSI|score|tier [0-9]/i);
  });

  it("appends spoken words and the listener reply to the thread", () => {
    const next = linesAfterSend([], "Sleep has been thin.", {
      session_id: "s1",
      reply: "A consistent wind-down can help.",
      crisis: false,
      accepted: true,
    });
    expect(next.map((line) => line.role)).toEqual(["you", "listener"]);
    expect(next[0]?.text).toBe("Sleep has been thin.");
  });

  it("keeps a crisis turn in the thread without a model reply shape", () => {
    const next = linesAfterCrisis([], "I want to die");
    expect(next[1]?.crisis).toBe(true);
    expect(next[1]?.text).toMatch(/stayed on this device/i);
  });
});

describe("personnel client", () => {
  it("posts a check-in without identifying fields", async () => {
    let body = "";
    const client = createPersonnelClient({
      baseUrl: "http://core.test",
      token: "t",
      fetchImpl: async (input, init) => {
        body = String(init?.body ?? "");
        expect(String(input)).toBe("http://core.test/v1/me/checkin");
        expect(String((init?.headers as Record<string, string>).Authorization)).toBe("Bearer t");
        return new Response(JSON.stringify({ observed_on: "2026-09-12", mood: 3 }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      },
    });
    const row = await client.submitCheckin({
      mood: 3,
      sleep_quality: 2,
      stress: 4,
      fatigue: 4,
      connection: 3,
    });
    expect(row.mood).toBe(3);
    expect(body).not.toMatch(/service_no|full_name|aadhaar/);
  });

  it("uploads audio to the server transcribe path, never a vendor host", async () => {
    const hosts: string[] = [];
    const client = createPersonnelClient({
      baseUrl: "http://core.test",
      token: "t",
      fetchImpl: async (input) => {
        hosts.push(String(input));
        return new Response(JSON.stringify({ transcript: "Sleep has been thin." }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      },
    });
    const text = await client.transcribe({
      uri: "file:///tmp/talk.m4a",
      name: "talk.m4a",
      type: "audio/m4a",
      language: "en",
    });
    expect(text).toBe("Sleep has been thin.");
    expect(hosts).toEqual(["http://core.test/v1/me/transcribe"]);
    expect(hosts.join()).not.toMatch(/deepgram/i);
  });
});
