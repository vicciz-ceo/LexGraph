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

## Running the app

Provisioning a real instance starts with bootstrap — one command creates the
first organization, matter, and admin user on an empty database, and prints
that admin's sign-in id (the id *is* the credential; there are no passwords):

```bash
cd backend && .venv/bin/python -m app.bootstrap --db dev.db
```

Flags (all optional — see `python -m app.bootstrap --help`): `--org-name`,
`--matter-name`, `--user-name`, `--user-email` customize the first
organization/matter/admin; `--db` points at a SQLite file (defaults to
`LEXGRAPH_DATABASE_URL` from the environment). Bootstrap refuses to run
against a database that already has users, so it's safe to leave in a
script. Copy the printed sign-in id, then start the servers:

```bash
cd backend && LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000
```

```bash
npm --prefix frontend install && npm --prefix frontend run dev
```

Open http://localhost:5173 and sign in with the id bootstrap printed. From
there, the signed-in admin creates further user accounts and grants them
matter roles from the in-app admin console (Admin → User accounts, then
Members & roles) — see [docs/RUNBOOK.md](docs/RUNBOOK.md#provisioning-users--access)
for the full walkthrough. No seed or mockup data is required for real use.

### Optional: demo workspace for local testing

`./scripts/demo.sh` is a local-testing convenience, not the provisioning
path: it sets up both environments, seeds a demo workspace (`admin`,
`reviewer`, `contributor`, `viewer` — the user id *is* the role name) into
`backend/dev.db`, and starts both servers in one command:

```bash
./scripts/demo.sh
```

Manually, the same demo seed is:

```bash
cd backend && .venv/bin/python -m app.seed_demo --db dev.db
```

The demo workspace ("MSA — Acme ↔ Blue Ridge Logistics" plus a second
matter) ships assertions in every status with ratings, comments, and
evidence, so the review queue, knowledge base, contested queue, analytics,
and admin console are all populated for exercising the UI — useful for
local development and mockup data, not for a real deployment.

The web UI (React, `frontend/src/pages/`) implements the Consensus design system — review queue, knowledge base, suggest-assertion flow, assertion detail, contested-queue adjudication, per-matter analytics, admin console, and profile/activity. [docs/design/consensus-ui-review.md](docs/design/consensus-ui-review.md) records the design review: what the mockups got wrong about the domain (votes/quorums vs. strength ratings, fabricated identity data, CDN dependencies) and how each screen was adapted.

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every PR and push to `main`: backend pytest on Python 3.12/3.13, frontend `tsc --noEmit` + Vitest on Node 24, and `scripts/contract_lint.sh` over the sprint contracts.

## Status

The collaborative-assertion feature set (see [docs/specs/collaborative-assertions.md](docs/specs/collaborative-assertions.md)) is implemented and test-covered: assertion CRUD with evidence and revisions, revision-scoped ratings with aggregates, comments, audit trail, review workflow with server-side per-matter permissions, matter isolation, hostile-input sanitization, graph projection, in-app notifications, search/sort/duplicate detection, eleven React components, and an end-to-end flow test.

Known limitations are recorded in the sprint contract under `docs/sprint/sprints/`. Notable ones: in-app notifications are held in process (not durable across restarts), and text that forms a syntactically valid HTML tag is stripped by the sanitizer (browser-faithful, but it drops those characters).

## License

LexGraph is free software, licensed under the [Apache License 2.0](LICENSE). You can self-host it, modify it, and embed it in your own products — including commercial and closed-source ones. The license includes an express patent grant from every contributor.

The license covers the platform code only. Documents, assertions, and any other content loaded into a LexGraph instance belong to the deploying organization and are governed by that organization's own terms and by the licenses of the source material — not by this license.
