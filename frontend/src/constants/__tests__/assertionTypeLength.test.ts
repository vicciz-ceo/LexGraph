// A proposed type name as the Suggest form saves it always fits what the API
// stores (backend NEW_ASSERTION_TYPE_MAX_LENGTH, the column's 255
// characters). The form lets a person type NEW_ASSERTION_TYPE_MAX_LENGTH
// characters, but upper case can make the saved name longer.

import { describe, expect, it } from "vitest";

import {
  ASSERTION_TYPE_STORED_MAX_LENGTH,
  NEW_ASSERTION_TYPE_MAX_LENGTH,
  normalizeAssertionType,
} from "../assertionTypes";

const characters = (value: string) => Array.from(value).length;

describe("proposed type name length", () => {
  it("keeps a name that upper case lengthens, up to what the API stores", () => {
    const typed = "ß".repeat(60);
    expect(typed.length).toBeLessThanOrEqual(NEW_ASSERTION_TYPE_MAX_LENGTH);
    expect(normalizeAssertionType(typed)).toBe("S".repeat(120));
  });

  it("cuts a longer saved name at the stored length", () => {
    const typed = "ﬃ".repeat(NEW_ASSERTION_TYPE_MAX_LENGTH); // each becomes FFI
    const saved = normalizeAssertionType(typed);
    expect(characters(saved)).toBe(ASSERTION_TYPE_STORED_MAX_LENGTH);
    expect(saved).toBe("FFI".repeat(85));
  });

  it("never ends a cut name with an underscore", () => {
    // "ᾷ" becomes Α, a combining mark and Ι: "Α_Ι" for each one typed.
    const saved = normalizeAssertionType("ᾷ".repeat(NEW_ASSERTION_TYPE_MAX_LENGTH));
    expect(characters(saved)).toBeLessThanOrEqual(ASSERTION_TYPE_STORED_MAX_LENGTH);
    expect(saved.endsWith("_")).toBe(false);
    expect(normalizeAssertionType("ab ".repeat(85) + "c")).toBe("AB_".repeat(84) + "AB");
  });

  it("counts characters, as the API does, not UTF-16 units", () => {
    const deseret = "𐐨".repeat(200); // one character each, two UTF-16 units
    expect(normalizeAssertionType(deseret)).toBe("𐐀".repeat(200));
  });
});
