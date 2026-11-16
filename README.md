# LexGraph

[![CI](https://github.com/vicciz-ceo/LexGraph/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/vicciz-ceo/LexGraph/actions/workflows/ci.yml)

A legal knowledge-graph platform: documents, provisions, and legal relationships modeled as versioned, evidence-backed assertions.

## Core concepts

- **Assertions** — versioned, collaborative propositions about graph entities (e.g. "a judgment interprets a statutory provision", "clause 8.4 creates an exception to clause 8.2"). Each assertion preserves its author, origin, evidence, revision history, review status, and temporal scope.
- **Evidence** — exact documentary source spans attached to assertions with explicit roles (supports, contradicts, qualifies, …).
- **Review workflow** — user- and model-suggested assertions start as drafts/proposals; only authorized reviewers can accept, reject, dispute, or supersede them.
- **User strength ratings** — per-user 1–5 assessments of an assertion *revision*, kept strictly separate from model confidence, evidentiary strength, formal review status, and legal validity. Ratings never change review status.
- **Graph projection** — accepted assertions are projected into a graph view; the relational database remains the authoritative store and any graph-side aggregate is a rebuildable projection. LexGraph ships and is tested on SQLite only. PostgreSQL and Neo4j, the stores the [spec](docs/specs/collaborative-assertions.md) names, are future work: no driver for either is installed.

## Layout

```
backend/     FastAPI + SQLAlchemy 2 + Pydantic v2 on SQLite (pytest)
frontend/    React 18 + TypeScript + Vite (Vitest + Testing Library)
docs/specs/  authoritative feature specifications
docs/sprint/ sprint contracts, acceptance gates, and run logs
```

## Running the tests

On a fresh clone, install both halves first, from the repository root. You
need Python 3.12 or later (`python3 --version`) and Node.js 22 (22.12 or
later) or 24:

```bash
(cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')
npm --prefix frontend ci
```

Then run both suites, also from the repository root:

```bash
backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run
```

## Running the app

Provisioning a real instance starts with bootstrap — one command creates the
first organization, matter, and admin user on an empty database, and prints
that admin's **sign-in token**. There are no passwords: each account has a
random sign-in token, shown once when it is issued; only a hash is stored.
User ids are public references (other members see them), never credentials.
Run every command below from the repository root:

```bash
(cd backend && .venv/bin/python -m app.bootstrap --db dev.db)
```

Flags (see `python -m app.bootstrap --help`): `--org-name`,
`--matter-name`, `--user-name`, `--user-email` customize the first
organization/matter/admin and are checked like the admin console's
fields (a valid email, stored in lowercase; names must not be blank);
`--db` points at a SQLite file. Without `--db`, bootstrap uses
`LEXGRAPH_DATABASE_URL`; with neither it refuses to run, because the
built-in default is an in-memory database that would vanish when it
exits. Bootstrap refuses to run against a database that already has
users, so it's safe to leave in a script. Copy the printed sign-in token
(it is not shown again; a lost token is replaced with
`python -m app.rotate_sign_in_token`, see
[docs/RUNBOOK.md](docs/RUNBOOK.md#sign-in-tokens-rotation-and-lockouts)),
then start the servers with the command it prints, for example:

```bash
(cd backend && LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000)
```

The web app needs Node.js 22 (22.12 or later) or 24; CI uses 24.

```bash
npm --prefix frontend ci && npm --prefix frontend run dev
```

Open http://localhost:5173 and sign in with the token bootstrap printed.
From there, the signed-in admin creates further user accounts (each shows
its new sign-in token once, to hand to its owner) and grants them matter
roles from the in-app admin console (Admin → User accounts, then Members &
roles) — see [docs/RUNBOOK.md](docs/RUNBOOK.md#provisioning-users--access)
for the full walkthrough. Email addresses are case-insensitive: they are
stored in lowercase, and no two accounts may share one. No seed or mockup
data is required for real use.

Upgrading a database created before sign-in tokens existed: apply the
migrations, after which every existing account signs in with its old user
id as a *legacy* token. Those are public, so rotate them — see the upgrade
note in [docs/RUNBOOK.md](docs/RUNBOOK.md#upgrading-sign-in-tokens-replace-user-id-sign-in).
The same migration run lowercases stored email addresses and makes them
unique; accounts that already share an address in different letter case
are reported and left for you to resolve
([docs/RUNBOOK.md](docs/RUNBOOK.md#upgrading-case-insensitive-emails)).

For a deployment, build the web app once instead of running the dev server.
The backend then serves it on its own port, same origin as the API (see
[docs/RUNBOOK.md](docs/RUNBOOK.md#serving-the-web-app-in-production)):

```bash
npm --prefix frontend ci && npm --prefix frontend run build   # then start uvicorn as above; open http://localhost:8000
```

After pulling a newer LexGraph, upgrade an existing database before starting
the server. The command is idempotent, and the server refuses to start on an
out-of-date database, printing this command with absolute paths:

```bash
(cd backend && .venv/bin/python -m app.migrate --db dev.db)
```

See [docs/RUNBOOK.md](docs/RUNBOOK.md#upgrading-an-existing-database-migration)
for what each migration changes.

### Optional: demo workspace for local testing

`./scripts/demo.sh` is a local-testing convenience, not the provisioning
path: it sets up both environments, seeds a demo workspace into
`backend/dev.db`, and starts both servers in one command. Sign in with the
demo sign-in tokens `admin`, `reviewer`, `contributor` or `viewer` (each is
also that account's user id, so anyone can sign in as any demo account; the
admin console flags them as legacy sign-ins). Ctrl-C stops both servers:

```bash
./scripts/demo.sh
```

It stops with an error when a port is taken or a server fails to start, and
it refuses, without changing it, a `dev.db` that is not a demo workspace,
such as the one `app.bootstrap` creates above. Pick other ports or another
database file with `BACKEND_PORT` (default 8000), `FRONTEND_PORT` (default
5173) and `DEMO_DB` (default `backend/dev.db`):

```bash
DEMO_DB=backend/demo.db BACKEND_PORT=8001 FRONTEND_PORT=5174 ./scripts/demo.sh
```

Running it again completes an interrupted first run (an install or seed cut short).

Manually, the same demo seed is:

```bash
(cd backend && .venv/bin/python -m app.seed_demo --db dev.db)
```

It refuses a file that already exists, such as a workspace from
`app.bootstrap`. Its `--reset` flag deletes the file first, whatever it
holds, so use `--reset` only on a demo database.

The demo workspace ("MSA — Acme ↔ Blue Ridge Logistics" plus a second
matter) ships assertions in every status with ratings, comments, and
evidence, so the review queue, knowledge base, contested queue, analytics,
and admin console are all populated for exercising the UI — useful for
local development and mockup data, not for a real deployment.

The web UI (React, `frontend/src/pages/`) implements the Consensus design system — review queue, knowledge base, suggest-assertion flow, assertion detail, contested-queue adjudication, per-matter analytics, admin console, and profile/activity. [docs/design/consensus-ui-review.md](docs/design/consensus-ui-review.md) records the design review: what the mockups got wrong about the domain (votes/quorums vs. strength ratings, fabricated identity data, CDN dependencies) and how each screen was adapted.

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every PR and push to `main`: backend pytest on Python 3.12/3.13, frontend `tsc --noEmit` + Vitest + the production build on Node 24, `npm audit` of the frontend dependencies (fails on high and critical advisories), shellcheck over `scripts/`, and `scripts/contract_lint.sh` over the sprint contracts.

## Local agents and lawyer authoring

Agents on Claude Code, Codex or any platform with local shell access can now
create validated, evidence-backed suggestions via MCP, JSON CLI, or REST. Read
[the agent guide](docs/AGENT_GUIDE.md) and [MCP setup](docs/mcp-registration.md).
Repository-level `AGENTS.md` and `CLAUDE.md` make the workflow discoverable.

Lawyers can search sources, suggest assertions, edit through recorded revisions,
submit/withdraw drafts, and rate each revision with a preserved rationale.
Agent provenance and exact evidence quotes are visible on assertion detail,
together with the review history and the rating rationales a member may read.
The detail page also attaches and removes evidence (for the author of an
unreviewed assertion, or a reviewer), threads the discussion with replies and
edits or deletes one's own comments, compares any two revisions field by field,
and lets reviewers mark an accepted assertion superseded by another accepted one.
Sources (documents, articles and their passages) are imported into a matter on
the server, not uploaded in the app; a new matter has none until then. See
[docs/RUNBOOK.md](docs/RUNBOOK.md#getting-sources-into-a-matter).

## Status

The collaborative-assertion feature set (see [docs/specs/collaborative-assertions.md](docs/specs/collaborative-assertions.md)) is implemented and test-covered: assertion CRUD with evidence and revisions, revision-scoped ratings with aggregates, comments, audit trail, review workflow with server-side per-matter permissions, matter isolation, hostile-input sanitization, graph projection (served by `GET /api/v1/matters/{id}/graph`; the web UI has no graph explorer yet), in-app notifications, search/sort/duplicate detection, the web UI described above, and an end-to-end flow test. Of the eleven React components the spec names (§14), the pages use eight: AssertionSuggestionForm (Suggest Assertion), AssertionReviewPanel (review queue, assertion detail), AssertionRatingDistribution (review queue, contested queue, assertion detail), and AssertionRatingWidget, AssertionEvidenceSelector, AssertionComments, AssertionRevisionHistory and AssertionComparisonView (assertion detail). AssertionCard, AssertionDetailPanel and RelatedAssertionsPanel are tested but not used by any page.

In-app notifications are stored in the database, so they survive restarts and every API worker serves the same feed; they link to their assertion and can be marked read (see [docs/RUNBOOK.md](docs/RUNBOOK.md#notifications)).

Known limitations are recorded in the sprint contract under `docs/sprint/sprints/`. A notable one: text that forms a syntactically valid HTML tag is stripped by the sanitizer (browser-faithful, but it drops those characters).

## License

LexGraph is free software, licensed under the [Apache License 2.0](LICENSE). You can self-host it, modify it, and embed it in your own products — including commercial and closed-source ones. The license includes an express patent grant from every contributor.

The license covers the platform code only. Documents, assertions, and any other content loaded into a LexGraph instance belong to the deploying organization and are governed by that organization's own terms and by the licenses of the source material — not by this license.
