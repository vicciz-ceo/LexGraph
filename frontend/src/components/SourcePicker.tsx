import { useEffect, useId, useState } from "react";
import { api } from "../api/client";

export interface SourceOption { id: string; type: string; label: string; quote_text?: string }

/** Search and page real local sources without requiring internal IDs. */
export function SourcePicker({ matterId, kind, label, value, onSelect }: {
  matterId: string; kind: "entities" | "source-spans"; label: string; value: string;
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
          id: item.id, type: item.type ?? "SourceSpan",
          label: item.label ?? `${item.document_title}: ${item.quote_text?.slice(0, 160)}`,
          quote_text: item.quote_text,
        })));
        setTotal(result.total); setError("");
      }).catch((e: unknown) => { if (!stale) setError(e instanceof Error ? e.message : "Unable to load sources"); })
        .finally(() => { if (!stale) setLoading(false); });
    }, 150);
    return () => { stale = true; window.clearTimeout(timer); };
  }, [matterId, kind, query, offset]);
  return <div className="field">
    <label htmlFor={`${id}-search`}>Search {label.toLowerCase()}</label>
    <input id={`${id}-search`} className="input" value={query} onChange={(e) => { setQuery(e.target.value); setOffset(0); }} />
    <label htmlFor={id}>{label}</label>
    <select id={id} className="input" value={value} onChange={(e) => {
      const option = items.find((item) => item.id === e.target.value) ?? null;
      setSelected(option); onSelect(option);
    }}>
      <option value="">Select a source</option>
      {value && !items.some((item) => item.id === value) && <option value={value}>{selected?.label ?? value}</option>}
      {items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
    </select>
    {selected?.quote_text && <blockquote>{selected.quote_text}</blockquote>}
    {loading && <span role="status">Searching sources…</span>}
    {error && <span role="alert">{error}</span>}
    {!loading && !error && total === 0 && <span>No matching sources. Import documents into this matter first, or change your search.</span>}
    <div>
      <button type="button" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous sources</button>
      <button type="button" disabled={offset + 50 >= total || loading} onClick={() => setOffset(offset + 50)}>More sources</button>
    </div>
  </div>;
}
