import "../styles/components/assertion-editor.css";

import { useState } from "react";
import type { AssertionDetail } from "../api/types";
import { api } from "../api/client";
import { Link } from "../app/router";
import { duplicateConflictOf, httpStatusOf } from "../constants/apiConflicts";
import { ASSERTION_TYPES } from "../constants/assertionTypes";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";

/** Same text for revision purposes: a textarea reports line breaks as LF. */
function sameText(a: string, b: string): boolean {
  return a.replace(/\r\n?/g, "\n") === b.replace(/\r\n?/g, "\n");
}

/** The revision fields besides the text that the editor can change (spec §3;
 * XREQ-50). Effective dates are calendar dates ("YYYY-MM-DD", "" for none). */
interface Facts {
  assertionType: string;
  jurisdiction: string;
  effectiveFrom: string;
  effectiveTo: string;
}

function calendarDate(value: string | null | undefined): string {
  return value && /^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0, 10) : "";
}

function factsOf(detail: AssertionDetail): Facts {
  return {
    assertionType: detail.assertion_type ?? "",
    jurisdiction: detail.jurisdiction ?? "",
    effectiveFrom: calendarDate(detail.effective_from),
    effectiveTo: calendarDate(detail.effective_to),
  };
}

/** PATCH fields for what differs from `base`; null clears an optional field.
 * Fields left alone are not sent, so a newer revision keeps its values. */
function changedFacts(facts: Facts, base: Facts): Record<string, string | null> {
  const body: Record<string, string | null> = {};
  if (facts.assertionType !== base.assertionType) body.assertion_type = facts.assertionType;
  if (facts.jurisdiction !== base.jurisdiction) body.jurisdiction = facts.jurisdiction || null;
  if (facts.effectiveFrom !== base.effectiveFrom) body.effective_from = facts.effectiveFrom || null;
  if (facts.effectiveTo !== base.effectiveTo) body.effective_to = facts.effectiveTo || null;
  return body;
}

const FACT_KEYS: (keyof Facts)[] = ["assertionType", "jurisdiction", "effectiveFrom", "effectiveTo"];

/** A draft's facts moved onto a newer revision (`latest`): each fact the user
 * changed from `base` keeps the user's value, every other takes the newer one. */
function rebaseFacts(facts: Facts, base: Facts, latest: Facts): Facts {
  const rebased = { ...latest };
  for (const key of FACT_KEYS) if (facts[key] !== base[key]) rebased[key] = facts[key];
  return rebased;
}

function labelize(value: string): string {
  const spaced = value.replace(/_/g, " ").toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

const FACT_LABELS: Record<keyof Facts, string> = {
  assertionType: "Assertion type",
  jurisdiction: "Jurisdiction",
  effectiveFrom: "Effective from",
  effectiveTo: "Effective to",
};

function factValueLabel(key: keyof Facts, value: string): string {
  if (value === "") return "none";
  if (key === "assertionType") return `${labelize(value)} (${value})`;
  if (key === "jurisdiction") return JURISDICTION_OPTIONS.find((o) => o.value === value)?.label ?? value;
  return value;
}

interface EditorError {
  message: string;
  /** Set for an exact-duplicate 409: the assertion that holds the text. */
  existingAssertionId?: string | null;
}

/** Edit, submit and withdraw controls on the assertion detail page.
 *
 * `onSaved` reloads the assertion. It runs after every successful action,
 * and `onReload` (default: `onSaved`) runs after a conflict, so the editor
 * can show the latest revision next to the user's unsaved changes: they are
 * never discarded by a failed save, and a stale-revision conflict can be
 * resolved in place (save them as the next revision, or start from the
 * latest one).
 *
 * A save sends only what the user changed, the text included: a field left
 * alone is not sent, so the API keeps its stored value, which may be a
 * colleague's newer one. */
export function AssertionEditor({ detail, canReview, isAuthor, onSaved, onReload }: {
  detail: AssertionDetail; canReview: boolean; isAuthor: boolean; onSaved: () => void;
  onReload?: () => void;
}) {
  const latestText = detail.proposition_raw ?? detail.proposition;
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(latestText);
  const [reason, setReason] = useState("");
  // The revision the open draft started from. When the page reloads a newer
  // revision, the draft is stale until the user decides.
  const [baseRevision, setBaseRevision] = useState(detail.current_revision_number);
  // What the user's changes are measured against: the newest revision the
  // open editor has seen (`seenRevision`).
  const [seenRevision, setSeenRevision] = useState(detail.current_revision_number);
  const [baseText, setBaseText] = useState(latestText);
  const [facts, setFacts] = useState<Facts>(() => factsOf(detail));
  const [baseFacts, setBaseFacts] = useState<Facts>(() => factsOf(detail));
  // A save answered 409 and the reload has not shown a newer revision yet.
  const [conflictPending, setConflictPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<EditorError | null>(null);
  const [notice, setNotice] = useState("");
  const reload = onReload ?? onSaved;

  // A newer revision reached the open editor (a colleague saved meanwhile, or
  // the reload after a 409). Rebase the draft onto it, here during render so
  // no stale value is ever shown: each field the user changed keeps their
  // value, every other one takes the newer revision's, the text included.
  // The form then shows what a save would store, and a save can no longer
  // put back an older wording the user never touched (review
  // fe-shell-authoring:1).
  if (editing && detail.current_revision_number !== seenRevision) {
    const newer = factsOf(detail);
    setSeenRevision(detail.current_revision_number);
    if (sameText(text, baseText)) setText(latestText);
    setBaseText(latestText);
    setFacts(rebaseFacts(facts, baseFacts, newer));
    setBaseFacts(newer);
  }

  const unreviewed = ["draft", "proposed", "revision_requested"].includes(detail.status);
  const canEdit = canReview || (isAuthor && unreviewed);
  // Keep an open draft, and the outcome of the last action, visible even if
  // the user may no longer edit (e.g. after withdrawing, or a conflict).
  if (!canEdit && !editing && !error && !notice) return null;

  const superseded = editing && detail.current_revision_number !== baseRevision;
  const latestFacts = factsOf(detail);
  const textChanged = !sameText(text, baseText);
  const factChanges = changedFacts(facts, baseFacts);
  const unchanged = !textChanged && Object.keys(factChanges).length === 0;
  const matchesLatest =
    sameText(text, latestText) && Object.keys(changedFacts(facts, latestFacts)).length === 0;
  // The user's own changes, as the conflict panel lists them: exactly what a
  // save sends.
  const ownChanges = [
    ...(textChanged ? ["Proposition: the text in the box below"] : []),
    ...FACT_KEYS.filter((key) => facts[key] !== baseFacts[key]).map(
      (key) => `${FACT_LABELS[key]}: ${factValueLabel(key, baseFacts[key])} → ${factValueLabel(key, facts[key])}`,
    ),
  ];
  const nothingToSave = matchesLatest || ownChanges.length === 0;
  const invertedDates =
    facts.effectiveFrom !== "" && facts.effectiveTo !== "" && facts.effectiveTo < facts.effectiveFrom;
  // The current type stays selectable even when it is not in the vocabulary
  // (a proposed new type, or an older value).
  const typeOptions = ASSERTION_TYPES.includes(baseFacts.assertionType) || !baseFacts.assertionType
    ? ASSERTION_TYPES
    : [baseFacts.assertionType, ...ASSERTION_TYPES];
  const jurisdictionKnown = JURISDICTION_OPTIONS.some((o) => o.value === baseFacts.jurisdiction);
  const setFact = (key: keyof Facts, value: string) => setFacts((current) => ({ ...current, [key]: value }));

  const startFromLatest = () => {
    setText(latestText); setBaseText(latestText);
    setBaseRevision(detail.current_revision_number); setSeenRevision(detail.current_revision_number);
    setFacts(latestFacts); setBaseFacts(latestFacts);
    setConflictPending(false); setError(null);
  };
  const startEditing = () => {
    startFromLatest();
    setReason(""); setNotice(""); setEditing(true);
  };
  const closeEditor = () => {
    setEditing(false); setConflictPending(false); setError(null);
  };

  /** Run an action; on failure keep every typed field and explain. */
  const run = async (action: () => Promise<unknown>, message: string, kind: "edit" | "status") => {
    if (busy) return;
    setBusy(true); setError(null); setNotice("");
    try {
      await action();
      setEditing(false); setReason(""); setConflictPending(false);
      setNotice(message); onSaved();
    } catch (e) {
      const duplicate = duplicateConflictOf(e);
      const status = httpStatusOf(e);
      if (duplicate !== null) {
        setError({
          message: kind === "edit"
            ? "Another assertion in this matter already states exactly this proposition, so the revision was not saved. Your text is still below."
            : "An identical proposition is already under review or accepted in this matter, so this draft cannot be submitted.",
          existingAssertionId: duplicate.existingAssertionId,
        });
      } else if (status === 409 || (status === 403 && kind === "status")) {
        // The page is showing an outdated assertion: reload it. The editor
        // stays mounted, so a draft survives and is compared below. (A
        // status action refused with 403 also means the assertion moved on,
        // e.g. it was withdrawn or reviewed meanwhile; it has no draft.)
        if (kind === "edit") setConflictPending(true);
        else setError({ message: "This assertion changed after this page was loaded (it may have been submitted, withdrawn or reviewed meanwhile), so the action was not applied. The page now shows its current state." });
        reload();
      } else if (status === 403) {
        // Not reloaded automatically: the draft must stay on screen.
        setError({ message: "You can no longer edit this assertion (it may have been reviewed, or your role changed). Your text has not been saved; copy it before leaving the page." });
      } else {
        setError({ message: e instanceof Error && e.message ? e.message : "Unable to save. Your changes are still here." });
      }
    } finally { setBusy(false); }
  };

  // Only the user's own changes: the text when they edited it, and the facts
  // they changed (changedFacts).
  const saveAsNextRevision = (expected: number | null) => run(() => api.updateAssertion(detail.id, {
    ...(textChanged ? { proposition: text } : {}), ...factChanges,
    revision_reason: reason.trim() || null, expected_revision_number: expected,
  }), "Revision saved. Previous ratings remain attached to their original revision.", "edit");

  const saveHint = !canEdit ? null
    : superseded ? "Choose how to handle the newer revision above before saving."
      : unchanged ? "Change the proposition or another field to save a new revision."
        : invertedDates ? "The effective end date cannot be before the start date." : null;

  return <section className="card"><div className="card__header">Edit and submit</div><div className="card__body">
    {error && <div role="alert" className="error-banner">
      <p>{error.message}</p>
      {error.existingAssertionId && <Link to={`/assertions/${error.existingAssertionId}`}>Open the existing assertion</Link>}
    </div>}
    {notice && <p role="status">{notice}</p>}
    {editing ? <>
      {!canEdit && <div role="alert" className="error-banner">
        <p>You can no longer edit this assertion (its status is now {detail.status.replace(/_/g, " ")}). Your text has not been saved; copy it if you want to keep it.</p>
      </div>}
      {canEdit && superseded && <div role="alert" className="error-banner assertion-editor__conflict">
        <p>A newer revision (v{detail.current_revision_number}) was saved while you were editing.
          {textChanged
            ? " Your text has not been saved and is still in the box below."
            : " You had not changed the text, so the box below now shows the newer one."}
          {" "}Fields you did not change show the newer revision's values.</p>
        <p>Latest saved text (v{detail.current_revision_number}):</p>
        <blockquote className="assertion-editor__latest">{latestText}</blockquote>
        {nothingToSave
          ? <p>Your changes are the same as the latest revision, so there is nothing to save.</p>
          : <>
            <p>Saving creates the next revision from the latest one, with only your changes:</p>
            <ul className="assertion-editor__changes" aria-label="Your changes">
              {ownChanges.map((change) => <li key={change}>{change}</li>)}
            </ul>
            <p>The newer revision stays in the history.</p>
          </>}
        <button type="button" className="btn btn--primary" disabled={busy || nothingToSave || !text.trim() || invertedDates}
          onClick={() => void saveAsNextRevision(detail.current_revision_number)}>
          Save my changes as the next revision</button>{" "}
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={startFromLatest}>
          Discard my changes and start from the latest</button>
      </div>}
      {canEdit && conflictPending && !superseded && <div role="alert" className="error-banner assertion-editor__conflict">
        <p>This assertion was changed after you started editing, so your revision was not saved.
          Your changes are still in the form below. Loading the latest version…</p>
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => reload()}>Reload latest version</button>
      </div>}
      <p>Saving creates a new revision. Earlier text and ratings remain in history; ratings are not copied to the new revision.</p>
      {detail.status === "accepted" && <p>This change will require review again.</p>}
      <div className="field"><label htmlFor="edit-proposition">Proposition</label>
        <textarea id="edit-proposition" className="textarea" value={text} onChange={(e) => setText(e.target.value)} /></div>
      <div className="assertion-editor__facts">
        <div className="field"><label htmlFor="edit-type">Assertion type</label>
          <select id="edit-type" className="select" value={facts.assertionType}
            onChange={(e) => setFact("assertionType", e.target.value)}>
            {!facts.assertionType && <option value="">Select assertion type…</option>}
            {typeOptions.map((type) => <option key={type} value={type}>{labelize(type)} ({type})</option>)}
          </select></div>
        <div className="field"><label htmlFor="edit-jurisdiction">Jurisdiction</label>
          <select id="edit-jurisdiction" className="select" value={facts.jurisdiction}
            onChange={(e) => setFact("jurisdiction", e.target.value)}>
            <option value="">No jurisdiction</option>
            {!jurisdictionKnown && baseFacts.jurisdiction &&
              <option value={baseFacts.jurisdiction}>{baseFacts.jurisdiction}</option>}
            {JURISDICTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select></div>
        <div className="field"><label htmlFor="edit-effective-from">Effective from</label>
          <input id="edit-effective-from" className="input" type="date" value={facts.effectiveFrom}
            onChange={(e) => setFact("effectiveFrom", e.target.value)} /></div>
        <div className="field"><label htmlFor="edit-effective-to">Effective to</label>
          <input id="edit-effective-to" className="input" type="date" value={facts.effectiveTo}
            onChange={(e) => setFact("effectiveTo", e.target.value)} /></div>
      </div>
      <div className="field"><label htmlFor="edit-reason">Reason for revision</label>
        {/* The API answers 422 for a revision_reason over 100,000 characters
            (validate_text_length); maxLength counts UTF-16 units, so it never lets more through. */}
        <input id="edit-reason" className="input" value={reason} maxLength={100000}
          onChange={(e) => setReason(e.target.value)} /></div>
      {saveHint && <p className="field__hint">{saveHint}</p>}
      <button className="btn btn--primary"
        disabled={busy || !canEdit || !text.trim() || unchanged || superseded || invertedDates}
        onClick={() => void saveAsNextRevision(baseRevision)}>Save revision</button>{" "}
      <button className="btn btn--secondary" disabled={busy} onClick={closeEditor}>Cancel edit</button>
    </> : canEdit && <>
      <button className="btn btn--secondary" disabled={busy} onClick={startEditing}>Edit assertion</button>{" "}
      {["draft", "revision_requested"].includes(detail.status) && <button className="btn btn--primary" disabled={busy}
        onClick={() => void run(() => api.submitAssertion(detail.id), "Submitted for review.", "status")}>Submit for review</button>}{" "}
      {unreviewed && <button className="btn btn--secondary" disabled={busy}
        onClick={() => void run(() => api.withdrawAssertion(detail.id), "Assertion withdrawn.", "status")}>Withdraw assertion</button>}
    </>}
  </div></section>;
}
