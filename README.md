# LexGraph

[![CI](https://github.com/vicciz-ceo/LexGraph/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/vicciz-ceo/LexGraph/actions/workflows/ci.yml)

A legal knowledge-graph platform: documents, provisions, and legal relationships modeled as versioned, evidence-backed assertions.

## Core concepts

- **Assertions** — versioned, collaborative propositions about graph entities (e.g. "a judgment interprets a statutory provision", "clause 8.4 creates an exception to clause 8.2"). Each assertion preserves its author, origin, evidence, revision history, review status, and temporal scope.
- **Evidence** — exact documentary source spans attached to assertions with explicit roles (supports, contradicts, qualifies, …).
- **Review workflow** — user- and model-suggested assertions start as drafts/proposals; only authorized reviewers can accept, reject, dispute, or supersede them.
- **User strength ratings** — per-user 1–5 assessments of an assertion *revision*, kept strictly separate from model confidence, evidentiary strength, formal review status, and legal validity. Ratings never change review status.
- **Graph projection** — accepted assertions are projected into a graph view; PostgreSQL remains the authoritative store and any graph-side aggregate is a rebuildable projection.

## Layout

```
backend/     FastAPI + SQLAlchemy 2 + Pydantic v2 (pytest)
frontend/    React 18 + TypeScript + Vite (Vitest + Testing Library)
docs/specs/  authoritative feature specifications
docs/sprint/ sprint contracts, acceptance gates, and run logs
```

## Running the tests

```bash
backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run
```

First-time backend setup:

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every PR and push to `main`: backend pytest on Python 3.12/3.13, frontend `tsc --noEmit` + Vitest on Node 24, and `scripts/contract_lint.sh` over the sprint contracts.

## Status

The collaborative-assertion feature set (see [docs/specs/collaborative-assertions.md](docs/specs/collaborative-assertions.md)) is implemented and test-covered: assertion CRUD with evidence and revisions, revision-scoped ratings with aggregates, comments, audit trail, review workflow with server-side per-matter permissions, matter isolation, hostile-input sanitization, graph projection, in-app notifications, search/sort/duplicate detection, eleven React components, and an end-to-end flow test.

Known limitations are recorded in the sprint contract under `docs/sprint/sprints/`. Notable ones: in-app notifications are held in process (not durable across restarts), and text that forms a syntactically valid HTML tag is stripped by the sanitizer (browser-faithful, but it drops those characters).

## License

LexGraph is free software, licensed under the [Apache License 2.0](LICENSE). You can self-host it, modify it, and embed it in your own products — including commercial and closed-source ones. The license includes an express patent grant from every contributor.

The license covers the platform code only. Documents, assertions, and any other content loaded into a LexGraph instance belong to the deploying organization and are governed by that organization's own terms and by the licenses of the source material — not by this license.
