import { describe, expect, it } from "vitest";

import { categoryList, consentLabel, roleLabel, shortToken } from "./format";

describe("display helpers", () => {
  it("names desks in plain language", () => {
    expect(roleLabel("medical_officer")).toBe("Medical officer");
  });

  it("shortens a vault token without dropping the tail", () => {
    expect(shortToken("tok_subject_0001")).toBe("tok_subj…0001");
  });

  it("renders consent and categories without scores", () => {
    expect(consentLabel(true)).toBe("granted");
    expect(categoryList([])).toBe("None recorded");
    expect(categoryList(["workload_and_duty"])).toBe("workload and duty");
  });
});
