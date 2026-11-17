// Supersede action for an accepted assertion (spec §1, §10, §13 POST
// /assertions/{id}/supersede; findings ui:15, pipeline:8). A reviewer or
// admin picks the accepted assertion of the same matter that replaces this
// one: from the related accepted assertions, or by searching. The caller
// decides who sees the panel and filters the candidates; this component
// only collects the choice and reports the outcome. A refused supersede
// keeps the form open with the server's reason.

import { useEffect, useId, useState } from "react";
import type { ReactElement } from "react";

export interface SupersedeCandidate {
  id: string;
  proposition: string;
}

export interface AssertionSupersedePanelProps {
  /** Candidates offered before any search (e.g. related accepted assertions). */
  suggestions: SupersedeCandidate[];
  /** Search the matter's eligible replacements (already filtered by the caller). */
  search: (query: string) => Promise<SupersedeCandidate[]>;
  onSupersede: (successorId: string) => Promise<void>;
}

/** Shorter queries are not sent: they would match most of a large matter. */
export const SUPERSEDE_MIN_QUERY_LENGTH = 2;
const SEARCH_DELAY_MS = 250;

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function AssertionSupersedePanel({
  suggestions,
  search,
  onSupersede,
}: AssertionSupersedePanelProps): ReactElement {
  const baseId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SupersedeCandidate[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (!open || trimmed.length < SUPERSEDE_MIN_QUERY_LENGTH) {
      setResults(null);
      setSearching(false);
      setSearchError(null);
      return;
    }
    let stale = false;
    setSearching(true);
    const timer = window.setTimeout(() => {
      search(trimmed)
        .then((items) => {
          if (stale) return;
          setResults(items);
          setSearchError(null);
        })
        .catch((err: unknown) => {
          if (!stale) setSearchError(messageOf(err, "The search failed."));
        })
        .finally(() => {
          if (!stale) setSearching(false);
        });
    }, SEARCH_DELAY_MS);
    return () => {
      stale = true;
      window.clearTimeout(timer);
    };
  }, [open, query, search]);

  const suggestedIds = new Set(suggestions.map((candidate) => candidate.id));
  const found = (results ?? []).filter((candidate) => !suggestedIds.has(candidate.id));
  // Only a choice that is still on screen can be submitted: a new search
  // that no longer lists the selected assertion clears the choice.
  const visibleIds = new Set([...suggestedIds, ...found.map((candidate) => candidate.id)]);
  const choice = selectedId !== null && visibleIds.has(selectedId) ? selectedId : null;

  const close = () => {
    setOpen(false);
    setQuery("");
    setSelectedId(null);
    setError(null);
  };

  async function handleSupersede() {
    if (choice === null || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onSupersede(choice);
      close();
    } catch (err) {
      setError(messageOf(err, "The assertion could not be superseded."));
    } finally {
      setBusy(false);
    }
  }

  const option = (candidate: SupersedeCandidate) => (
    <li key={candidate.id} className="adp-supersede-option">
      <label>
        <input
          type="radio"
          name={`${baseId}-successor`}
          value={candidate.id}
          checked={choice === candidate.id}
          onChange={() => setSelectedId(candidate.id)}
        />
        <span>{candidate.proposition}</span>
      </label>
      <a
        className="adp-supersede-open"
        href={`#/assertions/${encodeURIComponent(candidate.id)}`}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Open in a new tab: ${candidate.proposition}`}
      >
        Open
      </a>
    </li>
  );

  if (!open) {
    return (
      <div className="adp-supersede">
        <p className="adp-note">
          If a newer accepted assertion of this matter replaces this one, mark this one as
          superseded.
        </p>
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => setOpen(true)}>
          Mark as superseded…
        </button>
      </div>
    );
  }

  return (
    <div className="adp-supersede">
      <p className="adp-note">
        Choose the accepted assertion that replaces this one. This assertion&apos;s status becomes
        Superseded, and its page links to the replacement.
      </p>
      {suggestions.length > 0 && (
        <fieldset className="adp-supersede-group">
          <legend>Related accepted assertions</legend>
          <ul className="adp-supersede-options">{suggestions.map(option)}</ul>
        </fieldset>
      )}
      <div className="field adp-supersede-search">
        <label htmlFor={`${baseId}-search`}>Search accepted assertions</label>
        <input
          id={`${baseId}-search`}
          className="input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {query.trim().length < SUPERSEDE_MIN_QUERY_LENGTH ? (
          <span className="field__hint">
            Type at least {SUPERSEDE_MIN_QUERY_LENGTH} characters of the replacement&apos;s text.
          </span>
        ) : searching ? (
          <span className="field__hint" role="status">
            Searching…
          </span>
        ) : searchError ? (
          <span className="adp-supersede-error" role="alert">
            {searchError}
          </span>
        ) : (
          results !== null &&
          results.length === 0 && (
            <span className="field__hint">No other accepted assertion matches this search.</span>
          )
        )}
      </div>
      {found.length > 0 && (
        <fieldset className="adp-supersede-group">
          <legend>Search results</legend>
          <ul className="adp-supersede-options">{found.map(option)}</ul>
        </fieldset>
      )}
      {error && (
        <p className="adp-supersede-error" role="alert">
          {error}
        </p>
      )}
      <div className="adp-supersede-actions">
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={busy || choice === null}
          onClick={() => void handleSupersede()}
        >
          Supersede with selected assertion
        </button>
        <button type="button" className="btn btn--secondary btn--sm" disabled={busy} onClick={close}>
          Cancel
        </button>
      </div>
    </div>
  );
}
