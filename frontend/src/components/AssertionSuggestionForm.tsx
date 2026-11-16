import { SourcePicker } from "./SourcePicker";
import { useState } from "react";
import type { ChangeEvent, ReactElement } from "react";

import { Link } from "../app/router";
import {
  ASSERTION_TYPES,
  NEW_ASSERTION_TYPE_MAX_LENGTH,
  assertionTypeLabel,
  isRecognizedAssertionType,
  normalizeAssertionType,
} from "../constants/assertionTypes";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";
import { FURTHER_EVIDENCE_NOTE } from "../constants/suggestion";

// UI2 — assertion suggestion form (spec §6). Supports Method A (create
// from selected text — repository/matter/document/provision/quotation
// pre-populated) and Method B (create from graph entities — subject/
// object pre-populated from selected nodes), save-as-draft /
// submit-for-review / cancel / preview, multiple evidence spans with
// supporting/contradicting roles, a standalone-proposition option when
// there is no object entity, and a "needs further evidence" indicator.
// The assertion type is picked from the controlled vocabulary, or named
// as a proposed new type (spec §7). Types are local to this file (sprint
// ruling R7) — no shared types module this sprint.

/** Value of the type select's "Propose a new type…" option. */
const PROPOSE_NEW_TYPE = "__propose_new_type__";

export type AssertionSuggestionMethod = "selected_text" | "graph_entities";
export type EvidenceRole = "supports" | "contradicts";

export interface SelectedTextPrefill {
  method: "selected_text";
  repositoryId: string;
  matterId: string;
  documentVersionId?: string;
  provisionId?: string;
  sourceSpanId?: string;
  quotation?: string;
}

export interface GraphEntitiesPrefill {
  method: "graph_entities";
  repositoryId: string;
  matterId: string;
  subjectEntityId?: string;
  objectEntityId?: string;
  /** Display names for the entities (shown instead of their ids). */
  subjectEntityLabel?: string;
  objectEntityLabel?: string;
}

export type AssertionSuggestionPrefill = SelectedTextPrefill | GraphEntitiesPrefill;

export interface SimilarAssertion {
  id: string;
  /** "" when the text is not known; such matches are counted, never quoted. */
  proposition: string;
}

export interface EvidenceSpanInput {
  sourceSpanId: string;
  evidenceRole: EvidenceRole;
}

export interface AssertionSuggestionSubmission {
  method: AssertionSuggestionMethod;
  repositoryId: string;
  matterId: string;
  documentVersionId?: string;
  provisionId?: string;
  subjectEntityId?: string;
  objectEntityId?: string;
  standalone: boolean;
  /** A recognized type, or the normalized name of a proposed new type. */
  assertionType: string;
  /** True when `assertionType` is a new type the author proposes (spec §7). */
  assertionTypeIsProposedNew: boolean;
  proposition: string;
  explanation: string;
  jurisdiction?: string;
  effectiveStartDate?: string;
  effectiveEndDate?: string;
  evidence: EvidenceSpanInput[];
  needsFurtherEvidence: boolean;
  save_as: "draft" | "proposed";
}

export interface AssertionSuggestionFormProps {
  browseSources?: boolean;
  disabled?: boolean;
  prefill: AssertionSuggestionPrefill;
  onSubmit: (submission: AssertionSuggestionSubmission) => void;
  onCancel?: () => void;
  similarAssertions?: SimilarAssertion[];
  /** Every similar match, when more exist than `similarAssertions` lists. */
  similarAssertionsTotal?: number;
  /** Initial jurisdiction (e.g. the user's profile default); ignored unless
   * it is in the controlled vocabulary. */
  defaultJurisdiction?: string;
}

interface EvidenceRow {
  id: string;
  sourceSpanId: string;
  evidenceRole: EvidenceRole;
}

let rowCounter = 0;

function nextRowId(): string {
  rowCounter += 1;
  return `evidence-row-${rowCounter}`;
}

export function AssertionSuggestionForm({
  prefill,
  browseSources = false,
  disabled = false,
  onSubmit,
  onCancel,
  similarAssertions = [],
  similarAssertionsTotal,
  defaultJurisdiction,
}: AssertionSuggestionFormProps): ReactElement {
  const quotation = prefill.method === "selected_text" ? prefill.quotation : undefined;
  const documentVersionId = prefill.method === "selected_text" ? prefill.documentVersionId : undefined;
  const provisionId = prefill.method === "selected_text" ? prefill.provisionId : undefined;
  const sourceSpanId = prefill.method === "selected_text" ? prefill.sourceSpanId : undefined;
  const subjectEntityId = prefill.method === "graph_entities" ? prefill.subjectEntityId : undefined;
  const objectEntityId = prefill.method === "graph_entities" ? prefill.objectEntityId : undefined;

  const [proposition, setProposition] = useState("");
  // The select's value: a recognized type, PROPOSE_NEW_TYPE, or "" (none).
  const [typeChoice, setTypeChoice] = useState("");
  const [newTypeName, setNewTypeName] = useState("");
  const [explanation, setExplanation] = useState("");
  const [jurisdiction, setJurisdiction] = useState(() =>
    defaultJurisdiction && JURISDICTION_OPTIONS.some((option) => option.value === defaultJurisdiction)
      ? defaultJurisdiction
      : "",
  );
  const jurisdictionFromProfile = jurisdiction !== "" && jurisdiction === defaultJurisdiction;
  const [effectiveStartDate, setEffectiveStartDate] = useState("");
  const [effectiveEndDate, setEffectiveEndDate] = useState("");
  const [standalone, setStandalone] = useState(false);
  const [needsFurtherEvidence, setNeedsFurtherEvidence] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [evidenceRows, setEvidenceRows] = useState<EvidenceRow[]>(() =>
    sourceSpanId ? [{ id: nextRowId(), sourceSpanId, evidenceRole: "supports" }] : []
  );

  const proposingNewType = typeChoice === PROPOSE_NEW_TYPE;
  const normalizedNewType = normalizeAssertionType(newTypeName);
  const assertionType = proposingNewType ? normalizedNewType : typeChoice;
  const assertionTypeIsProposedNew =
    proposingNewType && normalizedNewType !== "" && !isRecognizedAssertionType(normalizedNewType);

  // Only matches whose text is known are quoted; the rest are counted.
  const namedSimilar = similarAssertions.filter((candidate) => candidate.proposition.trim() !== "");
  const similarTotal = Math.max(similarAssertionsTotal ?? 0, similarAssertions.length);
  const unnamedSimilarCount = similarTotal - namedSimilar.length;
  const hasExactDuplicate = namedSimilar.some(
    (candidate) => candidate.proposition.trim().toLowerCase() === proposition.trim().toLowerCase()
  );
  const propositionMissing = proposition.trim() === "";
  // Similarity warnings never block submission on their own (spec §7); an
  // exact duplicate does. When the caller has already surfaced possible
  // matches (similarAssertions is non-empty) the proposition-required
  // gate is considered satisfied by that upstream check.
  const submitDisabled = disabled || hasExactDuplicate || propositionMissing;

  const addEvidenceRow = () => {
    setEvidenceRows((rows) => [...rows, { id: nextRowId(), sourceSpanId: "", evidenceRole: "supports" }]);
  };

  const updateEvidenceRole = (id: string, role: EvidenceRole) => {
    setEvidenceRows((rows) => rows.map((row) => (row.id === id ? { ...row, evidenceRole: role } : row)));
  };

  const updateEvidenceSpanId = (id: string, value: string) => {
    setEvidenceRows((rows) => rows.map((row) => (row.id === id ? { ...row, sourceSpanId: value } : row)));
  };

  const removeEvidenceRow = (id: string) => {
    setEvidenceRows((rows) => rows.filter((row) => row.id !== id));
  };

  const buildSubmission = (saveAs: "draft" | "proposed"): AssertionSuggestionSubmission => ({
    method: prefill.method,
    repositoryId: prefill.repositoryId,
    matterId: prefill.matterId,
    documentVersionId,
    provisionId,
    subjectEntityId,
    objectEntityId: standalone ? undefined : objectEntityId,
    standalone,
    assertionType,
    assertionTypeIsProposedNew,
    proposition,
    explanation,
    jurisdiction: jurisdiction || undefined,
    effectiveStartDate: effectiveStartDate || undefined,
    effectiveEndDate: effectiveEndDate || undefined,
    evidence: evidenceRows.map(({ sourceSpanId: spanId, evidenceRole }) => ({ sourceSpanId: spanId, evidenceRole })),
    needsFurtherEvidence,
    save_as: saveAs,
  });

  const handleSaveDraft = () => {
    onSubmit(buildSubmission("draft"));
  };

  const handleSubmitForReview = () => {
    if (submitDisabled) {
      return;
    }
    onSubmit(buildSubmission("proposed"));
  };

  const handleCancel = () => {
    onCancel?.();
  };

  const handleTogglePreview = () => {
    setShowPreview((value) => !value);
  };

  return (
    <form className="assertion-suggestion-form" onSubmit={(event) => event.preventDefault()}>
      <h2>Suggest assertion</h2>

      {prefill.method === "selected_text" ? (
        <section className="assertion-suggestion-form__prefill">
          <dl>
            <dt>Repository</dt>
            <dd>{prefill.repositoryId}</dd>
            <dt>Matter</dt>
            <dd>{prefill.matterId}</dd>
            {documentVersionId ? (
              <>
                <dt>Document version</dt>
                <dd>{documentVersionId}</dd>
              </>
            ) : null}
            {provisionId ? (
              <>
                <dt>Provision</dt>
                <dd>{provisionId}</dd>
              </>
            ) : null}
          </dl>
          {quotation ? (
            <blockquote className="assertion-suggestion-form__quotation">
              Selected quotation: &ldquo;{quotation}&rdquo;
            </blockquote>
          ) : null}
        </section>
      ) : (
        <section className="assertion-suggestion-form__prefill">
          <dl>
            <dt>Repository</dt>
            <dd>{prefill.repositoryId}</dd>
            <dt>Matter</dt>
            <dd>{prefill.matterId}</dd>
            {subjectEntityId ? (
              <>
                <dt>Subject entity</dt>
                <dd title={subjectEntityId}>{prefill.subjectEntityLabel || subjectEntityId}</dd>
              </>
            ) : null}
            {objectEntityId ? (
              <>
                <dt>Object entity</dt>
                <dd title={objectEntityId}>{prefill.objectEntityLabel || objectEntityId}</dd>
              </>
            ) : null}
          </dl>
          <div className="assertion-suggestion-form__standalone">
            <label htmlFor="assertion-standalone">Standalone proposition (no object entity)</label>
            <input
              id="assertion-standalone"
              type="checkbox"
              checked={standalone}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setStandalone(event.target.checked)}
            />
          </div>
        </section>
      )}

      <div className="assertion-suggestion-form__field">
        <label htmlFor="assertion-type">Assertion type</label>
        <select
          id="assertion-type"
          value={typeChoice}
          onChange={(event) => setTypeChoice(event.target.value)}
        >
          <option value="">Select assertion type…</option>
          {ASSERTION_TYPES.map((type) => (
            <option key={type} value={type}>
              {assertionTypeLabel(type)} ({type})
            </option>
          ))}
          <option value={PROPOSE_NEW_TYPE}>Propose a new type…</option>
        </select>
      </div>

      {proposingNewType ? (
        <div className="assertion-suggestion-form__field assertion-suggestion-form__new-type">
          <label htmlFor="assertion-type-new">New type name</label>
          <input
            id="assertion-type-new"
            type="text"
            maxLength={NEW_ASSERTION_TYPE_MAX_LENGTH}
            value={newTypeName}
            aria-describedby="assertion-type-new-hint"
            onChange={(event) => setNewTypeName(event.target.value)}
          />
          <p id="assertion-type-new-hint" className="assertion-suggestion-form__hint">
            {normalizedNewType === ""
              ? "Name the relationship, for example “cancelled by”. It is saved in upper case with underscores."
              : isRecognizedAssertionType(normalizedNewType)
                ? `${normalizedNewType} is already a recognized type; it will be saved as ${normalizedNewType}.`
                : `Will be saved as ${normalizedNewType}, marked as a proposed new type.`}
          </p>
        </div>
      ) : null}

      <div className="assertion-suggestion-form__field">
        <label htmlFor="assertion-proposition">Proposition</label>
        <textarea
          id="assertion-proposition"
          value={proposition}
          onChange={(event) => setProposition(event.target.value)}
        />
      </div>

      {similarTotal > 0 ? (
        <div role="alert" className="assertion-suggestion-form__similarity-warning">
          <p>
            This proposition may repeat a similar assertion that already exists in this matter
            {namedSimilar.length > 0 ? ":" : "."}
          </p>
          {namedSimilar.length > 0 ? (
            <ul>
              {namedSimilar.map((candidate) => (
                <li key={candidate.id}>
                  <Link to={`/assertions/${candidate.id}`}>&ldquo;{candidate.proposition}&rdquo;</Link>
                </li>
              ))}
            </ul>
          ) : null}
          {unnamedSimilarCount > 0 ? (
            <p>
              {namedSimilar.length > 0
                ? `…and ${unnamedSimilarCount} more.`
                : `${unnamedSimilarCount} existing ${unnamedSimilarCount === 1 ? "assertion" : "assertions"} matched.`}
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="assertion-suggestion-form__field">
        <label htmlFor="assertion-explanation">Explanation or rationale</label>
        <textarea
          id="assertion-explanation"
          value={explanation}
          onChange={(event) => setExplanation(event.target.value)}
        />
      </div>

      <div className="assertion-suggestion-form__field">
        <label htmlFor="assertion-jurisdiction">Jurisdiction</label>
        <select
          id="assertion-jurisdiction"
          value={jurisdiction}
          aria-describedby={jurisdictionFromProfile ? "assertion-jurisdiction-hint" : undefined}
          onChange={(event) => setJurisdiction(event.target.value)}
        >
          <option value="">Select jurisdiction…</option>
          {JURISDICTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {jurisdictionFromProfile ? (
          <p id="assertion-jurisdiction-hint" className="assertion-suggestion-form__hint">
            Pre-selected from the default in your profile. Change it, or choose
            &ldquo;Select jurisdiction…&rdquo; to leave it unset.
          </p>
        ) : null}
      </div>

      <fieldset className="assertion-suggestion-form__effective-dates">
        <legend>Effective date range</legend>
        <label htmlFor="assertion-effective-start">Start date</label>
        <input
          id="assertion-effective-start"
          type="date"
          value={effectiveStartDate}
          onChange={(event) => setEffectiveStartDate(event.target.value)}
        />
        <label htmlFor="assertion-effective-end">End date</label>
        <input
          id="assertion-effective-end"
          type="date"
          value={effectiveEndDate}
          onChange={(event) => setEffectiveEndDate(event.target.value)}
        />
      </fieldset>

      <section className="assertion-suggestion-form__evidence">
        <h3>Evidence spans</h3>
        <ul>
          {evidenceRows.map((row) => (
            <li key={row.id} className="assertion-suggestion-form__evidence-row">
              {browseSources ? <SourcePicker matterId={prefill.matterId} kind="source-spans" label="Evidence source"
                value={row.sourceSpanId} onSelect={(option) => updateEvidenceSpanId(row.id, option?.id ?? "")} /> : <>
              <label htmlFor={`${row.id}-span`}>Source span</label>
              <input id={`${row.id}-span`} type="text" value={row.sourceSpanId}
                onChange={(event) => updateEvidenceSpanId(row.id, event.target.value)} />
              </>}

              <select
                aria-label="Evidence role"
                value={row.evidenceRole}
                onChange={(event) => updateEvidenceRole(row.id, event.target.value as EvidenceRole)}
              >
                <option value="supports">Supports</option>
                <option value="contradicts">Contradicts</option>
              </select>
              <button type="button" onClick={() => removeEvidenceRow(row.id)}>
                Remove evidence
              </button>
            </li>
          ))}
        </ul>
        <button type="button" onClick={addEvidenceRow}>
          Add evidence span
        </button>
      </section>

      <div className="assertion-suggestion-form__further-evidence">
        <label htmlFor="assertion-further-evidence-needed">Further evidence needed</label>
        <input
          id="assertion-further-evidence-needed"
          type="checkbox"
          checked={needsFurtherEvidence}
          aria-describedby="assertion-further-evidence-hint"
          onChange={(event) => setNeedsFurtherEvidence(event.target.checked)}
        />
      </div>
      <p id="assertion-further-evidence-hint" className="assertion-suggestion-form__hint">
        Adds a note to the explanation, which is saved as the first comment, so reviewers
        see that more evidence is needed.
      </p>

      {showPreview ? (
        <section className="assertion-suggestion-form__preview" aria-label="Preview">
          <h3>Preview</h3>
          <p>{proposition || "No proposition entered yet."}</p>
          {assertionType !== "" ? (
            <p>
              Type: {assertionType}
              {assertionTypeIsProposedNew ? " (proposed new type)" : ""}
            </p>
          ) : null}
          <p>{explanation}</p>
          {needsFurtherEvidence ? <p>{FURTHER_EVIDENCE_NOTE}</p> : null}
        </section>
      ) : null}

      <div className="assertion-suggestion-form__actions">
        <button type="button" onClick={handleSaveDraft} disabled={disabled || propositionMissing}>
          Save as draft
        </button>
        <button type="button" onClick={handleTogglePreview}>
          Preview
        </button>
        <button type="button" onClick={handleCancel}>
          Cancel
        </button>
        <button type="button" onClick={handleSubmitForReview} disabled={submitDisabled}>
          Submit for review
        </button>
      </div>
    </form>
  );
}
