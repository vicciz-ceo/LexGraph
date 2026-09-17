import { useState } from "react";
import type { AssertionDetail } from "../api/types";
import { api } from "../api/client";

export function AssertionEditor({ detail, canReview, isAuthor, onSaved }: {
  detail: AssertionDetail; canReview: boolean; isAuthor: boolean; onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(detail.proposition_raw ?? detail.proposition);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const unreviewed = ["draft", "proposed", "revision_requested"].includes(detail.status);
  if (!canReview && !(isAuthor && unreviewed)) return null;
  const run = async (action: () => Promise<unknown>, message: string) => {
    if (busy) return;
    setBusy(true); setError("");
    try { await action(); setEditing(false); setNotice(message); onSaved(); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to save. Your changes are still here."); }
    finally { setBusy(false); }
  };
  return <section className="card"><div className="card__header">Edit and submit</div><div className="card__body">
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {editing ? <>
      <p>Saving creates a new revision. Earlier text and ratings remain in history; ratings are not copied to the new revision.</p>
      {detail.status === "accepted" && <p>This change will require review again.</p>}
      <div className="field"><label htmlFor="edit-proposition">Proposition</label>
        <textarea id="edit-proposition" className="textarea" value={text} onChange={(e) => setText(e.target.value)} /></div>
      <div className="field"><label htmlFor="edit-reason">Reason for revision</label>
        <input id="edit-reason" className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></div>
      <button className="btn btn--primary" disabled={busy || !text.trim()} onClick={() => void run(() => api.updateAssertion(detail.id, {
        proposition: text, revision_reason: reason || null, expected_revision_number: detail.current_revision_number,
      }), "Revision saved. Previous ratings remain attached to their original revision.")}>Save revision</button>{" "}
      <button className="btn btn--secondary" disabled={busy} onClick={() => setEditing(false)}>Cancel edit</button>
    </> : <>
      <button className="btn btn--secondary" disabled={busy} onClick={() => { setText(detail.proposition_raw ?? detail.proposition); setEditing(true); }}>Edit assertion</button>{" "}
      {["draft", "revision_requested"].includes(detail.status) && <button className="btn btn--primary" disabled={busy}
        onClick={() => void run(() => api.submitAssertion(detail.id), "Submitted for review.")}>Submit for review</button>}{" "}
      {unreviewed && <button className="btn btn--secondary" disabled={busy}
        onClick={() => void run(() => api.withdrawAssertion(detail.id), "Assertion withdrawn.")}>Withdraw assertion</button>}
    </>}
  </div></section>;
}
