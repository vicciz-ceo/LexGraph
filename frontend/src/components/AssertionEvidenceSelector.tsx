import { useId, useState } from "react";
import type { ReactElement } from "react";

import {
  EVIDENCE_ROLE_LABELS,
  EVIDENCE_ROLES,
  SUPPORTING_EVIDENCE_ROLES,
  evidenceRoleLabel,
} from "../constants/evidence";
import type { EvidenceRole } from "../constants/evidence";
import { SourcePicker } from "./SourcePicker";
import type { SourceOption } from "./SourcePicker";

// Evidence list and editor (spec §2, §6, §8, §10), mounted on the assertion
// detail page (findings ui:15, pipeline:8). Lists the attached source
// passages with their role, document, quote and who attached them. When the
// caller allows it, a member can attach another passage of the matter, found
// with the real source search (GET /matters/{id}/source-spans), under any of
// the six evidence roles, and remove an attached one after confirming.
// Passages are always real span ids from the search; nothing is attached
// from free text.

export type { EvidenceRole };

export interface AssertionEvidenceItem {
  id: string;
  sourceSpanId: string;
  evidenceRole: string;
  /** The passage's text; empty when the span cannot be resolved. */
  quote: string;
  documentTitle?: string | null;
  /** Display name of the member who attached it. */
  addedBy?: string;
}

export interface NewEvidenceInput {
  sourceSpanId: string;
  evidenceRole: EvidenceRole;
  quote: string;
}

export interface AssertionEvidenceSelectorProps {
  /** The matter whose source passages can be attached. */
  matterId: string;
  evidence: AssertionEvidenceItem[];
  /** Omit to show the evidence without an attach form. */
  onAdd?: (input: NewEvidenceInput) => void | Promise<void>;
  /** Omit to offer no Remove action. */
  onRemove?: (evidenceId: string) => void | Promise<void>;
  /** Why an item may not be removed (its Remove is disabled), or null. */
  removalBlockedReason?: (item: AssertionEvidenceItem) => string | null;
  /** Shown instead of the list when nothing is attached. */
  emptyMessage?: string;
  /** Offer a "Further evidence needed" flag; only when the caller stores it. */
  needsFurtherEvidence?: boolean;
  onNeedsFurtherEvidenceChange?: (value: boolean) => void;
}

interface Feedback {
  kind: "status" | "error";
  message: string;
}

function roleBadgeClass(role: string): string {
  if (SUPPORTING_EVIDENCE_ROLES.has(role)) return "badge badge--accepted";
  if (role === "contradicts") return "badge badge--rejected";
  return "badge badge--neutral";
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function AssertionEvidenceSelector({
  matterId,
  evidence,
  onAdd,
  onRemove,
  removalBlockedReason,
  emptyMessage = "No evidence spans are linked to this assertion.",
  needsFurtherEvidence = false,
  onNeedsFurtherEvidenceChange,
}: AssertionEvidenceSelectorProps): ReactElement {
  const baseId = useId();
  const [attaching, setAttaching] = useState(false);
  const [selected, setSelected] = useState<SourceOption | null>(null);
  const [role, setRole] = useState<EvidenceRole>("supports");
  const [confirming, setConfirming] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [furtherEvidenceNeeded, setFurtherEvidenceNeeded] = useState(needsFurtherEvidence);

  const duplicate =
    selected !== null &&
    evidence.some((item) => item.sourceSpanId === selected.id && item.evidenceRole === role);

  const closeAttach = () => {
    setAttaching(false);
    setSelected(null);
    setRole("supports");
  };

  async function handleAttach() {
    if (!onAdd || !selected || duplicate || busy) return;
    setBusy(true);
    setFeedback(null);
    try {
      await onAdd({ sourceSpanId: selected.id, evidenceRole: role, quote: selected.quote_text ?? "" });
      closeAttach();
      setFeedback({ kind: "status", message: "Evidence attached." });
    } catch (error) {
      setFeedback({ kind: "error", message: messageOf(error, "The evidence could not be attached.") });
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(evidenceId: string) {
    if (!onRemove || busy) return;
    setBusy(true);
    setFeedback(null);
    try {
      await onRemove(evidenceId);
      setConfirming(null);
      setFeedback({ kind: "status", message: "Evidence removed." });
    } catch (error) {
      setConfirming(null);
      setFeedback({ kind: "error", message: messageOf(error, "The evidence could not be removed.") });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="assertion-evidence-selector">
      {evidence.length === 0 ? (
        <p className="muted">{emptyMessage}</p>
      ) : (
        <ul className="adp-evidence-list assertion-evidence-selector__list">
          {evidence.map((item) => {
            const sourceId = `${baseId}-source-${item.id}`;
            const blocked = onRemove ? (removalBlockedReason?.(item) ?? null) : null;
            const source =
              item.documentTitle ?? (item.quote ? "Quoted source" : "Source span unavailable");
            return (
              <li key={item.id} className="adp-evidence assertion-evidence-selector__item">
                <span className={`${roleBadgeClass(item.evidenceRole)} assertion-evidence-selector__role`}>
                  {evidenceRoleLabel(item.evidenceRole)}
                </span>
                <span id={sourceId} className={item.documentTitle ? undefined : "muted"}>
                  {source}
                </span>
                {item.quote && (
                  <blockquote className="assertion-evidence-selector__quote">{item.quote}</blockquote>
                )}
                {item.addedBy && <span className="muted adp-evidence-by">added by {item.addedBy}</span>}
                {onRemove && confirming !== item.id && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm adp-evidence-remove"
                    aria-describedby={sourceId}
                    disabled={busy || blocked !== null}
                    onClick={() => {
                      setFeedback(null);
                      setConfirming(item.id);
                    }}
                  >
                    Remove
                  </button>
                )}
                {onRemove && confirming !== item.id && blocked && (
                  <span className="field__hint adp-evidence-blocked">{blocked}</span>
                )}
                {onRemove && confirming === item.id && (
                  <span className="adp-evidence-confirm">
                    <span>Remove this passage from the assertion?</span>
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      disabled={busy}
                      onClick={() => void handleRemove(item.id)}
                    >
                      Remove evidence
                    </button>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      disabled={busy}
                      onClick={() => setConfirming(null)}
                    >
                      Keep
                    </button>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {onAdd &&
        (attaching ? (
          <div className="adp-evidence-attach assertion-evidence-selector__search">
            <SourcePicker
              matterId={matterId}
              kind="source-spans"
              label="Source passage"
              value={selected?.id ?? ""}
              onSelect={setSelected}
            />
            <div className="field">
              <label htmlFor={`${baseId}-role`}>Evidence role</label>
              <select
                id={`${baseId}-role`}
                className="input"
                value={role}
                onChange={(event) => setRole(event.target.value as EvidenceRole)}
              >
                {EVIDENCE_ROLES.map((value) => (
                  <option key={value} value={value}>
                    {EVIDENCE_ROLE_LABELS[value]}
                  </option>
                ))}
              </select>
              <span className="field__hint">
                Supports, Primary basis and Secondary basis count as supporting evidence; the
                other roles do not.
              </span>
            </div>
            {duplicate && (
              <p className="field__hint adp-evidence-duplicate">
                This passage is already attached with this role.
              </p>
            )}
            <div className="adp-evidence-attach-actions assertion-evidence-selector__actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={busy || selected === null || duplicate}
                onClick={() => void handleAttach()}
              >
                Attach selected passage
              </button>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                disabled={busy}
                onClick={closeAttach}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            className="btn btn--secondary btn--sm adp-evidence-attach-open"
            onClick={() => {
              setFeedback(null);
              setAttaching(true);
            }}
          >
            Attach evidence
          </button>
        ))}

      {onNeedsFurtherEvidenceChange && (
        <div className="assertion-evidence-selector__further-evidence">
          <label htmlFor={`${baseId}-further`}>Further evidence needed</label>
          <input
            id={`${baseId}-further`}
            type="checkbox"
            checked={furtherEvidenceNeeded}
            onChange={(event) => {
              setFurtherEvidenceNeeded(event.target.checked);
              onNeedsFurtherEvidenceChange(event.target.checked);
            }}
          />
        </div>
      )}

      {feedback && (
        <p
          className={feedback.kind === "error" ? "adp-evidence-error" : "adp-evidence-status"}
          role={feedback.kind === "error" ? "alert" : "status"}
        >
          {feedback.message}
        </p>
      )}
    </div>
  );
}
