import { describe, expect, it } from "vitest";

import { personnelCopy } from "./personnel";

describe("personnel copy", () => {
  it("keeps Hindi and English parallel without scores", () => {
    const en = personnelCopy("en");
    const hi = personnelCopy("hi");
    expect(Object.keys(en)).toEqual(Object.keys(hi));
    expect(en.lede.toLowerCase()).not.toContain("wsi");
    expect(hi.title).toContain("कल्याण");
  });
});
