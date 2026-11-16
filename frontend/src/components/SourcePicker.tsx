import "../styles/components/source-picker.css";

import { useEffect, useId, useState } from "react";
import { api } from "../api/client";

export interface SourceOption { id: string; type: string; label: string; quote_text?: string }

/** Page size of GET /matters/{id}/entities and /source-spans as the client requests them. */
export const SOURCE_PAGE_SIZE = 50;

/** Search and page real local sources without requiring internal IDs. */
export function SourcePicker({ matterId, kind, label, value, valueLabel, onSelect }: {
  matterId: string; kind: "entities" | "source-spans"; label: string; value: string;
  /** Display text for a `value` that is not among the loaded options (for
   * example a source pre-selected from a link), so the raw id never shows. */
  valueLabel?: string;
  onSelect: (option: SourceOption | null) => void;
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<SourceOption[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<SourceOption | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let stale = false;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api.sources(matterId, kind, query, offset).then((result) => {
        if (stale) return;
        setItems(result.items.map((item) => ({
          id: item.id, type: item.type ?? (kind === "entities" ? "Document" : "SourceSpan"),
          label: item.label ?? `${item.document_title}: ${item.quote_text?.slice(0, 160)}`,
          quote_text: item.quote_text,
        })));
        setTotal(result.total); setError("");
      }).catch((e: unknown) => { if (!stale) setError(e instanceof Error ? e.message : "Unable to load sources"); })
        .finally(() => { if (!stale) setLoading(false); });
    }, 150);
    return () => { stale = true; window.clearTimeout(timer); };
  }, [matterId, kind, query, offset]);
  const emptyMessage = query.trim() !== ""
    ? `No sources match “${query.trim()}”. Change your search.`
    : kind === "entities"
      ? "This matter has no documents or articles yet."
      : "This matter has no source passages yet.";
  const currentLabel = selected?.id === value ? selected.label : valueLabel ?? "Selected source";
  return <div className="field source-picker">
    <label htmlFor={`${id}-search`}>Search {label.toLowerCase()}</label>
    <input id={`${id}-search`} className="input" value={query} onChange={(e) => { setQuery(e.target.value); setOffset(0); }} />
    <label htmlFor={id}>{label}</label>
    <select id={id} className="input" value={value} onChange={(e) => {
      const option = items.find((item) => item.id === e.target.value) ?? null;
      setSelected(option); onSelect(option);
    }}>
      <option value="">Select a source</option>
      {value && !items.some((item) => item.id === value) && <option value={value}>{currentLabel}</option>}
      {items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
    </select>
    {selected?.quote_text && selected.id === value && <blockquote className="source-picker__quote">{selected.quote_text}</blockquote>}
    {loading && <span className="field__hint" role="status">Searching sources…</span>}
    {error && <span role="alert">{error}</span>}
    {!loading && !error && total === 0 && <span className="field__hint">{emptyMessage}</span>}
    {total > SOURCE_PAGE_SIZE && <div className="source-picker__pager">
      <span className="field__hint">
        Showing {Math.min(offset + 1, total)}–{Math.min(offset + items.length, total)} of {total}
      </span>
      <button type="button" className="btn btn--secondary btn--sm" disabled={offset === 0 || loading}
        onClick={() => setOffset(Math.max(0, offset - SOURCE_PAGE_SIZE))}>Previous sources</button>
      <button type="button" className="btn btn--secondary btn--sm" disabled={offset + SOURCE_PAGE_SIZE >= total || loading}
        onClick={() => setOffset(offset + SOURCE_PAGE_SIZE)}>More sources</button>
    </div>}
  </div>;
}
