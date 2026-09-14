import { describe, expect, it } from "vitest";

import { appendListener, appendYou, crisisNotice, prepareTalk } from "./talk";

describe("web talk", () => {
  it("holds crisis language on the desk before any model turn", () => {
    const next = prepareTalk("I want to die");
    expect(next.kind).toBe("crisis");
    expect(next.kind === "crisis" && next.holdOnDevice).toBe(true);
  });

  it("sends ordinary words after trim", () => {
    expect(prepareTalk("  The parade ground felt empty.  ")).toEqual({
      kind: "send",
      message: "The parade ground felt empty.",
    });
  });

  it("builds a thread without naming a score", () => {
    const you = appendYou([], "Sleep has been thin.");
    const next = appendListener(you, "A consistent wind-down can help.");
    expect(next.map((line) => line.role)).toEqual(["you", "listener"]);
    expect(crisisNotice().toLowerCase()).not.toMatch(/wsi|score/);
  });
});
