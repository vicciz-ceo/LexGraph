// Suggest Assertion — contributor authoring flow for a new
// user_suggested assertion (design: suggest_assertion screen, adapted).
// The form card wraps the existing AssertionSuggestionForm (graph_entities
// method); the page supplies subject/object entities into its prefill,
// maps the submission onto POST /assertions, surfaces similar-assertion
// matches returned by the backend, and navigates to the created
// assertion's detail page on success.

import "../styles/pages/suggest-assertion.css";

import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import { api, ApiError } from "../api/client";
import type { Assertion, MatterMembership } from "../api/types";
import { Link, navigate } from "../app/router";
import { useActiveSession } from "../app/session";
import { AssertionSuggestionForm } from "../components/AssertionSuggestionForm";
import type { AssertionSuggestionSubmission } from "../components/AssertionSuggestionForm";
import { SourcePicker } from "../components/SourcePicker";
import type { SourceOption } from "../components/SourcePicker";
import { duplicateConflictOf } from "../constants/apiConflicts";
import type { DuplicateConflict } from "../constants/apiConflicts";
import { ASSERTION_TYPES } from "../constants/assertionTypes";
import { readDefaultJurisdiction } from "../constants/preferences";
import {
  STATUS_LABELS,
  composeExplanation,
  summarizeSimilarAssertions,
} from "../constants/suggestion";
import type { SimilarAssertionMatch, SimilarAssertionsSummary } from "../constants/suggestion";

/** A subject or object the assertion is anchored to. */
interface EntityChoice {
  id: string;
  type: string;
  label: string;
}

/** An entity named by a deep link: `?subject=<id>[&subject_type=<Type>]`
 * (same for `object`). Graph views that know the node's type pass it. */
interface EntityLink {
  id: string;
  type: string | null;
}

type EntitiesPage = Awaited<ReturnType<typeof api.sources>>;

/** How many pages of the matter's documents and articles are searched for
 * the id of a link that does not say its type. */
const LINK_LOOKUP_PAGES = 20;

/** Read a deep-linked entity from the current hash query once, at mount
 * (no subscription to hash changes). */
function initialEntityLink(role: "subject" | "object"): EntityLink | null {
  const raw = window.location.hash.replace(/^#/, "");
  const query = new URLSearchParams(raw.split("?")[1] ?? "");
  const id = (query.get(role) ?? "").trim();
  if (id === "") return null;
  const type = (query.get(`${role}_type`) ?? "").trim();
  return { id, type: /^[A-Za-z][A-Za-z0-9_]*$/.test(type) ? type : null };
}

async function findMatterEntity(
  matterId: string,
  id: string,
  firstPage: EntitiesPage | null,
): Promise<EntityChoice | null> {
  let offset = 0;
  for (let page = 0; page < LINK_LOOKUP_PAGES; page += 1) {
    const result =
      page === 0 && firstPage !== null ? firstPage : await api.sources(matterId, "entities", "", offset);
    const hit = result.items.find((item) => item.id === id);
    if (hit) return { id, type: hit.type ?? "Document", label: hit.label ?? "Linked source" };
    offset += result.items.length;
    if (result.items.length === 0 || offset >= result.total) return null;
  }
  return null;
}

/** Resolve a deep-linked entity to its real type and a display name. A
 * link without a type is looked up among the matter's documents and
 * articles, then its assertions; one that cannot be found is not used
 * (it is never sent under a guessed type). A link that states its type is
 * used as given — the API validates it on save. */
async function resolveEntityLink(
  matterId: string,
  link: EntityLink,
  firstPage: EntitiesPage | null,
): Promise<EntityChoice | null> {
  if (link.type === null || link.type === "Document" || link.type === "Article") {
    const found = await findMatterEntity(matterId, link.id, firstPage);
    if (found) return found;
  }
  if (link.type === null || link.type === "Assertion") {
    try {
      const assertion = await api.getAssertion(link.id);
      if (assertion.matter_id === matterId) {
        return { id: link.id, type: "Assertion", label: `Assertion: ${assertion.proposition}` };
      }
    } catch {
      // Not an assertion of this matter.
    }
  }
  if (link.type !== null) {
    return { id: link.id, type: link.type, label: `${humanizeEntityType(link.type)} from the link you followed` };
  }
  return null;
}

/** "SourceSpan" -> "Source span". */
function humanizeEntityType(type: string): string {
  const words = type.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Older backends send only {assertion_id, match_kind, score}: load the
 * text of the listed matches so the notice never shows bare ids. */
async function withPropositions(items: SimilarAssertionMatch[]): Promise<SimilarAssertionMatch[]> {
  return Promise.all(
    items.map(async (item) => {
      if (item.proposition !== "") return item;
      try {
        const existing = await api.getAssertion(item.id);
        return { ...item, proposition: existing.proposition, status: existing.status };
      } catch {
        return item;
      }
    }),
  );
}

function SimilarNotice({
  created,
  similar,
  onSuggestAnother,
}: {
  created: Assertion;
  similar: SimilarAssertionsSummary;
  onSuggestAnother: () => void;
}): ReactElement {
  const isProposed = created.status === "proposed";
  const more = similar.total - similar.items.length;
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
          {similar.items.map((item) => (
            <li key={item.id} className="sa-similar__item">
              <span className="sa-similar__proposition">
                {item.proposition !== "" ? (
                  item.proposition
                ) : (
                  <span className="muted">An existing assertion (its text could not be loaded)</span>
                )}
              </span>
              <span className="sa-similar__meta">
                {item.status !== null && (
                  <span className={`badge badge--${item.status}`}>
                    {STATUS_LABELS[item.status] ?? item.status}
                  </span>
                )}
                <Link className="btn btn--secondary btn--sm" to={`/assertions/${item.id}`}>
                  View
                </Link>
              </span>
            </li>
          ))}
        </ul>
        {more > 0 && (
          <p className="sa-similar__more">
            &hellip;and {more} more {more === 1 ? "similar assertion" : "similar assertions"} not
            listed here.
          </p>
        )}
        <div className="sa-similar__actions">
          <button type="button" className="btn btn--secondary" onClick={onSuggestAnother}>
            Suggest another assertion
          </button>
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

function DuplicateBanner({ duplicate }: { duplicate: DuplicateConflict }): ReactElement {
  return (
    <div className="error-banner sa-duplicate" role="alert">
      <p>
        <strong>This exact proposition already exists in this matter, so nothing was saved.</strong>
      </p>
      <p>
        Open the existing assertion to rate it, discuss it or add your evidence there. If you
        are making a different claim, state how it differs.
      </p>
      {duplicate.existingAssertionId !== null && (
        <Link className="btn btn--secondary btn--sm" to={`/assertions/${duplicate.existingAssertionId}`}>
          Open the existing assertion
        </Link>
      )}
    </div>
  );
}

/** ui:33 — a matter with no documents (e.g. a freshly bootstrapped
 * workspace) cannot anchor an assertion; say how sources get in. */
function NoSourcesState({
  matter,
  onCheckAgain,
  checking,
}: {
  matter: MatterMembership;
  onCheckAgain: () => void;
  checking: boolean;
}): ReactElement {
  return (
    <section className="card sa-empty" aria-labelledby="sa-empty-title">
      <div className="card__body">
        <h2 id="sa-empty-title" className="empty-state__title">
          This matter has no sources yet
        </h2>
        <p>
          Every assertion is anchored to a document or article of its matter and cites
          passages from it as evidence, so {matter.name} needs imported documents before
          assertions can be suggested in it.
        </p>
        <p>
          Documents are not uploaded in the web app. An administrator of this LexGraph
          installation imports them on the server with the ingest commands described in
          the runbook (<span className="mono">docs/RUNBOOK.md</span>, &ldquo;Getting sources
          into a matter&rdquo;). The import needs this matter&rsquo;s identifiers:
        </p>
        <dl className="sa-empty__ids">
          <dt>Matter ID</dt>
          <dd className="mono">{matter.id}</dd>
          <dt>Repository ID</dt>
          <dd className="mono">{matter.repository_id}</dd>
        </dl>
        <p>Imported documents and their passages appear here as soon as they are stored.</p>
        <button type="button" className="btn btn--secondary" disabled={checking} onClick={onCheckAgain}>
          {checking ? "Checking…" : "Check again"}
        </button>
      </div>
    </section>
  );
}

function SuggestWorkspace({
  matter,
  userId,
  onReset,
}: {
  matter: MatterMembership;
  userId: string;
  onReset: () => void;
}): ReactElement {
  const [links] = useState(() => ({
    subject: initialEntityLink("subject"),
    object: initialEntityLink("object"),
  }));
  const [subject, setSubject] = useState<EntityChoice | null>(null);
  const [object, setObject] = useState<EntityChoice | null>(null);
  const [resolvingLinks, setResolvingLinks] = useState(links.subject !== null || links.object !== null);
  const [linkNotices, setLinkNotices] = useState<string[]>([]);
  // null until the first entities page answers (the form renders meanwhile).
  const [hasSources, setHasSources] = useState<boolean | null>(null);
  const [checkingSources, setCheckingSources] = useState(false);
  const [defaultJurisdiction] = useState(() => readDefaultJurisdiction(userId));
  const [error, setError] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState<DuplicateConflict | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<Assertion | null>(null);
  const [similar, setSimilar] = useState<SimilarAssertionsSummary>({ items: [], total: 0 });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      let firstPage: EntitiesPage | null = null;
      try {
        firstPage = await api.sources(matter.id, "entities", "", 0);
        if (!cancelled) setHasSources(firstPage.total > 0);
      } catch {
        // Unknown: keep the form; the pickers report the error themselves.
        if (!cancelled) setHasSources(true);
      }
      const notices: string[] = [];
      for (const role of ["subject", "object"] as const) {
        const link = links[role];
        if (link === null) continue;
        const choice = await resolveEntityLink(matter.id, link, firstPage).catch(() => null);
        if (cancelled) return;
        if (choice !== null) {
          (role === "subject" ? setSubject : setObject)(choice);
        } else {
          notices.push(
            `The ${role} in the link you followed is not a document or article of this matter, ` +
              `so it was not filled in. Choose the ${role} source below.`,
          );
        }
      }
      if (!cancelled) {
        setLinkNotices(notices);
        setResolvingLinks(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [matter.id, links]);

  const checkSourcesAgain = async () => {
    setCheckingSources(true);
    try {
      const page = await api.sources(matter.id, "entities", "", 0);
      setHasSources(page.total > 0);
    } catch {
      // Leave the empty state; the next check can succeed.
    } finally {
      setCheckingSources(false);
    }
  };

  const prefill = {
    method: "graph_entities" as const,
    repositoryId: matter.repository_id,
    matterId: matter.id,
    subjectEntityId: subject?.id,
    objectEntityId: object?.id,
    subjectEntityLabel: subject?.label,
    objectEntityLabel: object?.label,
  };

  const pick = (option: SourceOption | null): EntityChoice | null =>
    option === null ? null : { id: option.id, type: option.type, label: option.label };

  const handleSubmission = async (submission: AssertionSuggestionSubmission) => {
    if (busy || created || resolvingLinks) return;
    setError(null);
    setDuplicate(null);

    if (subject === null || (submission.subjectEntityId ?? "") === "") {
      setError("Select a source for the subject of this assertion.");
      return;
    }
    if (submission.proposition.trim() === "") {
      setError("Enter a proposition — the single claim this assertion makes.");
      return;
    }
    if (submission.assertionType.trim() === "") {
      setError("Select an assertion type, or name the new type you are proposing.");
      return;
    }

    const objectChoice = submission.objectEntityId ? object : null;
    const body = {
      repository_id: submission.repositoryId,
      matter_id: submission.matterId,
      assertion_type: submission.assertionType.trim(),
      ...(submission.assertionTypeIsProposedNew ? { assertion_type_is_proposed_new: true } : {}),
      proposition: submission.proposition,
      subject_entity: { type: subject.type, id: subject.id },
      object_entity: objectChoice !== null ? { type: objectChoice.type, id: objectChoice.id } : null,
      jurisdiction: submission.jurisdiction?.trim() || null,
      effective_from: submission.effectiveStartDate || null,
      effective_to: submission.effectiveEndDate || null,
      evidence: submission.evidence
        .filter((row) => row.sourceSpanId.trim() !== "")
        .map((row) => ({
          source_span_id: row.sourceSpanId.trim(),
          evidence_role: row.evidenceRole,
        })),
      explanation: composeExplanation(submission.explanation, submission.needsFurtherEvidence),
      save_as: submission.save_as,
    };

    setBusy(true);
    try {
      const result = await api.createAssertion(body);
      const summary = summarizeSimilarAssertions(result);
      if (summary.items.length > 0 || summary.total > 0) {
        // First save that came back with lookalikes: stay on the page and
        // surface them (also fed into the form's similarity warning)
        // instead of silently continuing to the detail page.
        const items = await withPropositions(summary.items);
        setCreated(result);
        setSimilar({ items, total: summary.total });
      } else {
        navigate(`/assertions/${result.id}`);
      }
    } catch (err) {
      const conflict = duplicateConflictOf(err);
      if (conflict !== null) {
        setDuplicate(conflict);
      } else if (err instanceof ApiError) {
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
        {duplicate !== null && <DuplicateBanner duplicate={duplicate} />}
        {created !== null && (
          <SimilarNotice created={created} similar={similar} onSuggestAnother={onReset} />
        )}

        {hasSources === false && created === null && !resolvingLinks && subject === null ? (
          <NoSourcesState matter={matter} checking={checkingSources} onCheckAgain={() => void checkSourcesAgain()} />
        ) : (
          <section className="card sa-form-card">
            <div className="card__body">
              {resolvingLinks && (
                <p className="muted sa-link-status" role="status">
                  Looking up the source from the link you followed…
                </p>
              )}
              {linkNotices.map((notice) => (
                <p key={notice} className="sa-link-notice">
                  {notice}
                </p>
              ))}
              <div className="sa-entity-fields">
                <SourcePicker matterId={matter.id} kind="entities" label="Subject source"
                  value={subject?.id ?? ""} valueLabel={subject?.label}
                  onSelect={(option) => setSubject(pick(option))} />
                <SourcePicker matterId={matter.id} kind="entities" label="Object source (optional)"
                  value={object?.id ?? ""} valueLabel={object?.label}
                  onSelect={(option) => setObject(pick(option))} />
              </div>

              <AssertionSuggestionForm
                prefill={prefill}
                browseSources
                disabled={busy || created !== null || resolvingLinks}
                onSubmit={(submission) => {
                  void handleSubmission(submission);
                }}
                onCancel={() => navigate("/knowledge")}
                similarAssertions={similar.items}
                similarAssertionsTotal={similar.total}
                defaultJurisdiction={defaultJurisdiction}
              />
              {busy && (
                <p className="muted sa-saving" role="status">
                  Saving assertion…
                </p>
              )}
            </div>
          </section>
        )}
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
                {ASSERTION_TYPES.map((type) => (
                  <span key={type} className="chip chip--tag">
                    {type}
                  </span>
                ))}
              </div>
              <p className="field__hint">
                For a relationship outside this list, choose &ldquo;Propose a new
                type&hellip;&rdquo; in the type field and name it; the assertion is
                saved with that type, marked as a proposed new type.
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
  // Bumped by "Suggest another assertion" to start over with a fresh form.
  const [round, setRound] = useState(0);

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
        <SuggestWorkspace
          key={`${session.user.id}:${session.currentMatter.id}:${round}`}
          matter={session.currentMatter}
          userId={session.user.id}
          onReset={() => setRound((value) => value + 1)}
        />
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
