import "../styles/components/assertion-editor.css";

import { useState } from "react";
import type { AssertionDetail } from "../api/types";
import { api } from "../api/client";
import { Link } from "../app/router";
import { duplicateConflictOf, httpStatusOf } from "../constants/apiConflicts";

/** Same text for revision purposes: a textarea reports line breaks as LF. */
function sameText(a: string, b: string): boolean {
  return a.replace(/\r\n?/g, "\n") === b.replace(/\r\n?/g, "\n");
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
 * can show the latest revision next to the user's unsaved text: the text
 * is never discarded by a failed save, and a stale-revision conflict can
 * be resolved in place (save the text as the next revision, or start from
 * the latest one). */
export function AssertionEditor({ detail, canReview, isAuthor, onSaved, onReload }: {
  detail: AssertionDetail; canReview: boolean; isAuthor: boolean; onSaved: () => void;
  onReload?: () => void;
}) {
  const latestText = detail.proposition_raw ?? detail.proposition;
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(latestText);
  const [reason, setReason] = useState("");
  // The revision (and its text) the open draft started from. When the page
  // reloads a newer revision, the draft is stale until the user decides.
  const [baseRevision, setBaseRevision] = useState(detail.current_revision_number);
  const [baseText, setBaseText] = useState(latestText);
  // A save answered 409 and the reload has not shown a newer revision yet.
  const [conflictPending, setConflictPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<EditorError | null>(null);
  const [notice, setNotice] = useState("");
  const reload = onReload ?? onSaved;
  const unreviewed = ["draft", "proposed", "revision_requested"].includes(detail.status);
  const canEdit = canReview || (isAuthor && unreviewed);
  // Keep an open draft, and the outcome of the last action, visible even if
  // the user may no longer edit (e.g. after withdrawing, or a conflict).
  if (!canEdit && !editing && !error && !notice) return null;

  const superseded = editing && detail.current_revision_number !== baseRevision;
  const unchanged = sameText(text, baseText);
  const matchesLatest = sameText(text, latestText);

  const startEditing = () => {
    setText(latestText); setBaseText(latestText); setBaseRevision(detail.current_revision_number);
    setReason(""); setError(null); setNotice(""); setConflictPending(false); setEditing(true);
  };
  const startFromLatest = () => {
    setText(latestText); setBaseText(latestText); setBaseRevision(detail.current_revision_number);
    setConflictPending(false); setError(null);
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

  const saveAsNextRevision = (expected: number | null) => run(() => api.updateAssertion(detail.id, {
    proposition: text, revision_reason: reason.trim() || null, expected_revision_number: expected,
  }), "Revision saved. Previous ratings remain attached to their original revision.", "edit");

  const saveHint = !canEdit ? null
    : superseded ? "Choose how to handle the newer revision above before saving."
      : unchanged ? "Change the proposition to save a new revision." : null;

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
          Your text has not been saved and is still in the box below.</p>
        <p>Latest saved text (v{detail.current_revision_number}):</p>
        <blockquote className="assertion-editor__latest">{latestText}</blockquote>
        {matchesLatest
          ? <p>Your text is the same as the latest revision, so there is nothing to save.</p>
          : <p>Compare it with your text. Saving yours creates the next revision; the newer one stays in the history.</p>}
        <button type="button" className="btn btn--primary" disabled={busy || matchesLatest || !text.trim()}
          onClick={() => void saveAsNextRevision(detail.current_revision_number)}>
          Save my text as the next revision</button>{" "}
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={startFromLatest}>
          Discard my text and start from the latest</button>
      </div>}
      {canEdit && conflictPending && !superseded && <div role="alert" className="error-banner assertion-editor__conflict">
        <p>This assertion was changed after you started editing, so your revision was not saved.
          Your text is still in the box below. Loading the latest version…</p>
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => reload()}>Reload latest version</button>
      </div>}
      <p>Saving creates a new revision. Earlier text and ratings remain in history; ratings are not copied to the new revision.</p>
      {detail.status === "accepted" && <p>This change will require review again.</p>}
      <div className="field"><label htmlFor="edit-proposition">Proposition</label>
        <textarea id="edit-proposition" className="textarea" value={text} onChange={(e) => setText(e.target.value)} /></div>
      <div className="field"><label htmlFor="edit-reason">Reason for revision</label>
        <input id="edit-reason" className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></div>
      {saveHint && <p className="field__hint">{saveHint}</p>}
      <button className="btn btn--primary"
        disabled={busy || !canEdit || !text.trim() || unchanged || superseded}
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
