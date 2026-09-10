import { describe, expect, it } from "vitest";

import { homeFor } from "./session";

describe("homeFor", () => {
  it("sends a medical officer to the clinical desk, not the welfare queue", () => {
    expect(homeFor("medical_officer")).toBe("/clinical");
    expect(homeFor("welfare_officer")).toBe("/officer");
  });
});
