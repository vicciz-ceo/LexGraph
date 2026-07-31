// Suggest Assertion — contributor authoring flow for a new
// user_suggested assertion (design: suggest_assertion screen, adapted).
// The form card wraps the existing AssertionSuggestionForm (graph_entities
// method); the page supplies subject/object entity ids into its prefill,
// maps the submission onto POST /assertions, surfaces similar-assertion
// matches returned by the backend, and navigates to the created
// assertion's detail page on success.

import "../styles/pages/suggest-assertion.css";

import { useState } from "react";
import type { ReactElement } from "react";

import { api, ApiError } from "../api/client";
import type { Assertion, MatterMembership } from "../api/types";
import { Link, navigate } from "../app/router";
import { useActiveSession } from "../app/session";
import { AssertionSuggestionForm } from "../components/AssertionSuggestionForm";
import type {
  AssertionSuggestionSubmission,
  SimilarAssertion,
} from "../components/AssertionSuggestionForm";

// Controlled assertion-type vocabulary, mirrored from
// backend/app/services/validation.py (ALLOWED_ASSERTION_TYPES). Shown as
// guidance only — the backend remains the enforcement point.
const RECOGNIZED_ASSERTION_TYPES = [
  "INTERPRETS",
  "CREATES_EXCEPTION_TO",
  "CONFLICTS_WITH",
  "MODIFIES",
  "APPLIES_TO",
  "RELEVANT_TO",
  "WEAKENS",
  "SUPPORTS",
  "SURVIVES_TERMINATION",
  "DISTINGUISHABLE_FROM",
  "USES_DEFINITION",
  "DERIVES_FROM_LAW",
];

/** Read an entity id from the current hash query (e.g. /suggest?subject=…)
 * once, at mount — supports deep links from graph views without
 * subscribing to hash changes. */
function initialEntityParam(name: string): string {
  const raw = window.location.hash.replace(/^#/, "");
  const queryPart = raw.split("?")[1] ?? "";
  return new URLSearchParams(queryPart).get(name) ?? "";
}

/** The wire shape of createAssertion's similar_assertions has carried both
 * {id, proposition} and related-match ({assertion_id, …}) forms — normalize
 * to what AssertionSuggestionForm expects. */
function normalizeSimilars(
  raw: { id: string; proposition: string }[] | undefined,
): SimilarAssertion[] {
  return (raw ?? [])
    .map((item) => {
      const match = item as { id?: string; assertion_id?: string; proposition?: string };
      return { id: match.id ?? match.assertion_id ?? "", proposition: match.proposition ?? "" };
    })
    .filter((item) => item.id !== "");
}

function SimilarNotice({
  created,
  similar,
}: {
  created: Assertion;
  similar: SimilarAssertion[];
}): ReactElement {
  const isProposed = created.status === "proposed";
  return (
    <section className="card sa-similar" aria-live="polite">
      <div className="card__header">
        <span>Similar assertions already exist</span>
        <span className={`badge badge--${created.status}`}>
          {isProposed ? "Proposed" : "Draft"}
        </span>
      </div>
      <div className="card__body">
        <p className="sa-similar__note">
          Your assertion was saved{" "}
          {isProposed ? "and submitted for review" : "as a draft"}, but this matter
          already has assertions that look similar. If one of them covers your
          claim, open it and add a strength rating instead of keeping a duplicate.
        </p>
        <ul className="sa-similar__list">
          {similar.map((item) => (
            <li key={item.id} className="sa-similar__item">
              <span className="sa-similar__proposition">
                {item.proposition !== "" ? (
                  item.proposition
                ) : (
                  <span className="mono">{item.id}</span>
                )}
              </span>
              <Link className="btn btn--secondary btn--sm" to={`/assertions/${item.id}`}>
                View
              </Link>
            </li>
          ))}
        </ul>
        <div className="sa-similar__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => navigate(`/assertions/${created.id}`)}
          >
            Continue to your assertion
          </button>
        </div>
      </div>
    </section>
  );
}

function SuggestWorkspace({ matter }: { matter: MatterMembership }): ReactElement {
  const [subjectEntityId, setSubjectEntityId] = useState(() => initialEntityParam("subject"));
  const [objectEntityId, setObjectEntityId] = useState(() => initialEntityParam("object"));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<Assertion | null>(null);
  const [similar, setSimilar] = useState<SimilarAssertion[]>([]);

  const prefill = {
    method: "graph_entities" as const,
    repositoryId: matter.repository_id,
    matterId: matter.id,
    subjectEntityId: subjectEntityId.trim() || undefined,
    objectEntityId: objectEntityId.trim() || undefined,
  };

  const handleSubmission = async (submission: AssertionSuggestionSubmission) => {
    if (busy) return;
    setError(null);

    const subjectId = submission.subjectEntityId?.trim() ?? "";
    if (subjectId === "") {
      setError(
        "Enter a subject entity ID — every assertion must be anchored to a graph entity in this matter.",
      );
      return;
    }
    if (submission.proposition.trim() === "") {
      setError("Enter a proposition — the single claim this assertion makes.");
      return;
    }
    if (submission.assertionType.trim() === "") {
      setError("Enter an assertion type (see the recognized types in the side panel).");
      return;
    }

    const objectId = submission.objectEntityId?.trim() ?? "";
    const body = {
      repository_id: submission.repositoryId,
      matter_id: submission.matterId,
      assertion_type: submission.assertionType.trim(),
      proposition: submission.proposition.trim(),
      subject_entity: { type: "Entity", id: subjectId },
      object_entity: objectId !== "" ? { type: "Entity", id: objectId } : null,
      jurisdiction: submission.jurisdiction?.trim() || null,
      effective_from: submission.effectiveStartDate || null,
      effective_to: submission.effectiveEndDate || null,
      evidence: submission.evidence
        .filter((row) => row.sourceSpanId.trim() !== "")
        .map((row) => ({
          source_span_id: row.sourceSpanId.trim(),
          evidence_role: row.evidenceRole,
        })),
      explanation: submission.explanation.trim() || null,
      save_as: submission.save_as,
    };

    setBusy(true);
    try {
      const result = await api.createAssertion(body);
      const matches = normalizeSimilars(result.similar_assertions);
      if (matches.length > 0 && created === null) {
        // First save that came back with lookalikes: stay on the page and
        // surface them (also fed into the form's similarity warning)
        // instead of silently continuing to the detail page.
        setCreated(result);
        setSimilar(matches);
      } else {
        navigate(`/assertions/${result.id}`);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Saving the assertion failed. Check your connection and try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="sa-layout">
      <div className="sa-main">
        {error !== null && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        {created !== null && <SimilarNotice created={created} similar={similar} />}

        <section className="card sa-form-card">
          <div className="card__body">
            <div className="sa-entity-fields">
              <div className="field">
                <label htmlFor="sa-subject-entity">Subject entity ID</label>
                <input
                  id="sa-subject-entity"
                  className="input"
                  type="text"
                  value={subjectEntityId}
                  onChange={(event) => setSubjectEntityId(event.target.value)}
                  placeholder="Graph entity this assertion is about"
                />
                <span className="field__hint">
                  Required. Copy the entity&rsquo;s ID from the Knowledge Base graph.
                </span>
              </div>
              <div className="field">
                <label htmlFor="sa-object-entity">Object entity ID</label>
                <input
                  id="sa-object-entity"
                  className="input"
                  type="text"
                  value={objectEntityId}
                  onChange={(event) => setObjectEntityId(event.target.value)}
                  placeholder="Second entity, if the claim relates two"
                />
                <span className="field__hint">
                  Optional — leave empty (or tick standalone) for a one-entity claim.
                </span>
              </div>
            </div>

            <AssertionSuggestionForm
              prefill={prefill}
              onSubmit={(submission) => {
                void handleSubmission(submission);
              }}
              onCancel={() => navigate("/knowledge")}
              similarAssertions={similar}
            />
            {busy && (
              <p className="muted sa-saving" role="status">
                Saving assertion…
              </p>
            )}
          </div>
        </section>
      </div>

      <aside className="sa-rail">
        <section className="card">
          <div className="card__header">How suggestions work</div>
          <div className="card__body">
            <ol className="sa-help__steps">
              <li>
                <strong>Draft or propose.</strong> &ldquo;Save as draft&rdquo; keeps the
                assertion out of the review queue until you are ready;
                &ldquo;Submit for review&rdquo; proposes it immediately.
              </li>
              <li>
                <strong>Review.</strong> A reviewer accepts, rejects, disputes, or
                requests revision. Colleague strength ratings inform the standing
                grade but never change the review decision.
              </li>
              <li>
                <strong>Evidence.</strong> Evidence spans reference source spans from
                this matter&rsquo;s documents. An assertion without supporting
                evidence is marked unsupported, and accepting it requires a written
                justification from the reviewer.
              </li>
            </ol>
            <p className="sa-help__origin">
              Your suggestion carries the <span className="chip chip--user">Colleague</span>{" "}
              chip and sits in the same queue as{" "}
              <span className="chip chip--model">AI-deduced</span> assertions.
            </p>
          </div>
        </section>

        <section className="card">
          <div className="card__header">Writing a strong assertion</div>
          <div className="card__body">
            <ul className="sa-help__tips">
              <li>State one clear, verifiable claim per assertion.</li>
              <li>
                Anchor it to the right graph entities — the subject is what the claim
                is about.
              </li>
              <li>
                Set jurisdiction and effective dates when the claim is time- or
                place-bound.
              </li>
              <li>Attach the evidence spans that support — or contradict — the claim.</li>
              <li>
                If a similar assertion already exists, add a strength rating to it
                instead of duplicating it.
              </li>
            </ul>
            <div className="sa-help__types">
              <p className="sa-help__types-label">Recognized assertion types</p>
              <div className="sa-help__types-chips">
                {RECOGNIZED_ASSERTION_TYPES.map((type) => (
                  <span key={type} className="chip chip--tag">
                    {type}
                  </span>
                ))}
              </div>
              <p className="field__hint">
                Types outside this list are rejected by validation unless explicitly
                proposed as new types.
              </p>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}

export function SuggestAssertionPage(): ReactElement {
  const session = useActiveSession();
  const canSuggest =
    session.role === "contributor" || session.role === "reviewer" || session.role === "admin";

  return (
    <div className="sa-page">
      <header className="page-header">
        <div>
          <h1 className="page-header__title">Suggest Assertion</h1>
          <p className="page-header__subtitle">
            Contribute a new legal assertion to {session.currentMatter.name}. Your
            suggestion enters the same review queue as AI-deduced assertions.
          </p>
        </div>
      </header>

      {canSuggest ? (
        <SuggestWorkspace key={session.currentMatter.id} matter={session.currentMatter} />
      ) : (
        <div className="empty-state">
          <p className="empty-state__title">Contributor role required</p>
          <p>
            Your role on this matter is view-only. Ask a matter admin for the
            contributor role to suggest assertions.
          </p>
        </div>
      )}
    </div>
  );
}
