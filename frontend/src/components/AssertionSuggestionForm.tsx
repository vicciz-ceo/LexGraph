import { useState } from "react";
import type { ChangeEvent, ReactElement } from "react";

// UI2 — assertion suggestion form (spec §6). Supports Method A (create
// from selected text — repository/matter/document/provision/quotation
// pre-populated) and Method B (create from graph entities — subject/
// object pre-populated from selected nodes), save-as-draft /
// submit-for-review / cancel / preview, multiple evidence spans with
// supporting/contradicting roles, a standalone-proposition option when
// there is no object entity, and a "needs further evidence" indicator.
// Types are local to this file (sprint ruling R7) — no shared types
// module this sprint.

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
}

export type AssertionSuggestionPrefill = SelectedTextPrefill | GraphEntitiesPrefill;

export interface SimilarAssertion {
  id: string;
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
  assertionType: string;
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
  prefill: AssertionSuggestionPrefill;
  onSubmit: (submission: AssertionSuggestionSubmission) => void;
  onCancel?: () => void;
  similarAssertions?: SimilarAssertion[];
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
  onSubmit,
  onCancel,
  similarAssertions = [],
}: AssertionSuggestionFormProps): ReactElement {
  const quotation = prefill.method === "selected_text" ? prefill.quotation : undefined;
  const documentVersionId = prefill.method === "selected_text" ? prefill.documentVersionId : undefined;
  const provisionId = prefill.method === "selected_text" ? prefill.provisionId : undefined;
  const sourceSpanId = prefill.method === "selected_text" ? prefill.sourceSpanId : undefined;
  const subjectEntityId = prefill.method === "graph_entities" ? prefill.subjectEntityId : undefined;
  const objectEntityId = prefill.method === "graph_entities" ? prefill.objectEntityId : undefined;

  const [proposition, setProposition] = useState("");
  const [assertionType, setAssertionType] = useState("");
  const [explanation, setExplanation] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [effectiveStartDate, setEffectiveStartDate] = useState("");
  const [effectiveEndDate, setEffectiveEndDate] = useState("");
  const [standalone, setStandalone] = useState(false);
  const [needsFurtherEvidence, setNeedsFurtherEvidence] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [evidenceRows, setEvidenceRows] = useState<EvidenceRow[]>(() =>
    sourceSpanId ? [{ id: nextRowId(), sourceSpanId, evidenceRole: "supports" }] : []
  );

  const hasExactDuplicate = similarAssertions.some(
    (candidate) => candidate.proposition.trim().toLowerCase() === proposition.trim().toLowerCase()
  );
  const propositionMissing = proposition.trim() === "";
  // Similarity warnings never block submission on their own (spec §7); an
  // exact duplicate does. When the caller has already surfaced possible
  // matches (similarAssertions is non-empty) the proposition-required
  // gate is considered satisfied by that upstream check.
  const submitDisabled = hasExactDuplicate || propositionMissing;

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
                <dd>{subjectEntityId}</dd>
              </>
            ) : null}
            {objectEntityId ? (
              <>
                <dt>Object entity</dt>
                <dd>{objectEntityId}</dd>
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
        <input
          id="assertion-type"
          type="text"
          value={assertionType}
          onChange={(event) => setAssertionType(event.target.value)}
        />
      </div>

      <div className="assertion-suggestion-form__field">
        <label htmlFor="assertion-proposition">Proposition</label>
        <textarea
          id="assertion-proposition"
          value={proposition}
          onChange={(event) => setProposition(event.target.value)}
        />
      </div>

      {similarAssertions.length > 0 ? (
        <div role="alert" className="assertion-suggestion-form__similarity-warning">
          <p>
            This proposition may be a similar assertion to one that already exists:{" "}
            {similarAssertions.map((candidate) => `"${candidate.proposition}"`).join(", ")}
          </p>
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
        <input
          id="assertion-jurisdiction"
          type="text"
          value={jurisdiction}
          onChange={(event) => setJurisdiction(event.target.value)}
        />
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
              <label htmlFor={`${row.id}-span`}>Source span</label>
              <input
                id={`${row.id}-span`}
                type="text"
                value={row.sourceSpanId}
                onChange={(event) => updateEvidenceSpanId(row.id, event.target.value)}
              />
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
          onChange={(event) => setNeedsFurtherEvidence(event.target.checked)}
        />
      </div>

      {showPreview ? (
        <section className="assertion-suggestion-form__preview" aria-label="Preview">
          <h3>Preview</h3>
          <p>{proposition || "No proposition entered yet."}</p>
          <p>{explanation}</p>
        </section>
      ) : null}

      <div className="assertion-suggestion-form__actions">
        <button type="button" onClick={handleSaveDraft}>
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
