// Instants from the LexGraph REST API.
//
// The API returns every instant as UTC with an explicit offset ("…Z" or
// "+00:00"). Older servers wrote SQLite values back without one, e.g.
// "2026-11-15T20:16:17.835814", and ECMAScript reads an offset-less
// date-time as LOCAL time, so the UTC digits showed as the viewer's wall
// clock (audit finding ui:3). parseApiInstant reads such a value as UTC and
// leaves a value that carries an offset as it is.
//
// effective_from / effective_to are calendar dates, not instants. Never pass
// them through these helpers: that would shift them by the viewer's offset.
//
// A plain module, not part of client.ts, so pages can import it while their
// tests mock the API client.

const DATE_TIME = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/;
const HAS_OFFSET = /(?:Z|[+-]\d{2}:?\d{2})$/i;

const DATE_OPTIONS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "numeric",
};

/** The instant an API timestamp denotes; null when absent or unparseable. */
export function parseApiInstant(value: string | null | undefined): Date | null {
  if (!value) return null;
  let text = value.trim();
  if (DATE_TIME.test(text)) {
    // ECMAScript guarantees millisecond precision only; Python sends
    // microseconds.
    text = text.replace(" ", "T").replace(/(\.\d{3})\d+/, "$1");
    if (!HAS_OFFSET.test(text)) text += "Z";
  }
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "Nov 15, 2026" in the viewer's timezone, or "—". */
export function formatInstantDate(value: string | null | undefined, locale?: string): string {
  const date = parseApiInstant(value);
  return date === null ? "—" : date.toLocaleDateString(locale, DATE_OPTIONS);
}

/** Date and time in the viewer's timezone (the locale's default format
 * unless `options` say otherwise), or "—". */
export function formatInstantDateTime(
  value: string | null | undefined,
  locale?: string,
  options?: Intl.DateTimeFormatOptions,
): string {
  const date = parseApiInstant(value);
  return date === null ? "—" : date.toLocaleString(locale, options);
}

/** ISO-8601 UTC ("…Z"), e.g. for an export; an unparseable value as it is. */
export function instantToIso(value: string | null | undefined): string {
  return parseApiInstant(value)?.toISOString() ?? value ?? "";
}
