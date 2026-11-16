// matchPath decodes route parameters, but a malformed percent-escape in a
// hand-edited or truncated link must not throw: decodeURIComponent raised
// "URIError: URI malformed" during render and blanked the whole app, and a
// reload kept the same hash (finding ui:27).

import { describe, expect, it } from "vitest";

import { matchPath } from "../router";

describe("matchPath", () => {
  it("decodes percent-escaped parameters", () => {
    expect(matchPath("/assertions/:id", "/assertions/a%2Fb%20c")).toEqual({ id: "a/b c" });
    expect(matchPath("/assertions/:id", "/assertions/%D7%93%D7%A0%D7%94")).toEqual({ id: "דנה" });
  });

  it("treats a malformed percent-escape as no match instead of throwing", () => {
    expect(() => matchPath("/assertions/:id", "/assertions/%E0%A4%A")).not.toThrow();
    expect(matchPath("/assertions/:id", "/assertions/%E0%A4%A")).toBeNull();
    expect(matchPath("/assertions/:id", "/assertions/100%")).toBeNull();
  });

  it("still requires literal segments and lengths to match", () => {
    expect(matchPath("/assertions/:id", "/knowledge/1")).toBeNull();
    expect(matchPath("/assertions/:id", "/assertions/1/extra")).toBeNull();
  });
});
