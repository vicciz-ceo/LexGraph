# LexGraph

A legal knowledge-graph platform: documents, provisions, and legal relationships modeled as versioned, evidence-backed assertions.

## Core concepts

- **Assertions** — versioned, collaborative propositions about graph entities (e.g. "a judgment interprets a statutory provision", "clause 8.4 creates an exception to clause 8.2"). Each assertion preserves its author, origin, evidence, revision history, review status, and temporal scope.
- **Evidence** — exact documentary source spans attached to assertions with explicit roles (supports, contradicts, qualifies, …).
- **Review workflow** — user- and model-suggested assertions start as drafts/proposals; only authorized reviewers can accept, reject, dispute, or supersede them.
- **User strength ratings** — per-user 1–5 assessments of an assertion revision, kept strictly separate from model confidence, evidentiary strength, formal review status, and legal validity.
- **Graph projection** — accepted assertions are projected into Neo4j; PostgreSQL remains the authoritative store.

## Status

Early development. See `docs/` for sprint specifications.
