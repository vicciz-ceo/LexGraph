# LexGraph Local-First Install Runbook

This runbook describes how to set up and run a complete local-first LexGraph system from a fresh clone, with zero cloud dependencies. The system consists of:
1. A local SQLite database
2. A FastAPI backend server
3. A React web application (the Consensus UI)
4. An MCP server for agent integration

## Fresh-Clone Setup

Start with a clean clone of the repository:

```bash
git clone https://github.com/vicciz-ceo/LexGraph.git
cd LexGraph
```

You need Python 3.12 or later (`python3 --version`; CI tests 3.12 and 3.13) and Node.js 22 (22.12 or later) or 24 with npm.

### Quickstart (real provisioning)

The real path from an empty database to a working, admin-owned instance:
bootstrap the workspace, sign in as the admin bootstrap creates, then
provision further users and access from the app itself.

```bash
(cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')
cd backend
.venv/bin/python -m app.bootstrap --db dev.db
```

Bootstrap refuses to run on a non-empty database (an empty-DB guard — no
silent mutation on top of an existing workspace; the check runs before it
creates any table) and prints the new admin's
**sign-in token**: a random secret, shown this once, of which only a hash is
stored (`backend/app/auth.py`; requests send `Authorization: Bearer <token>`).
There are no passwords. User ids are public references, not credentials.
It needs a database to write to: `--db PATH`, or else
`LEXGRAPH_DATABASE_URL`. With neither (or an in-memory URL) it exits with
an error instead of bootstrapping the throwaway in-memory default, and it
also rejects a blank organization, matter or admin name and an invalid
admin email before touching the database (exit code 2).
Copy the token (if it is lost, see
["Sign-in tokens, rotation and lockouts"](#sign-in-tokens-rotation-and-lockouts)),
then start the backend, still in `backend/` (bootstrap prints the exact
command for your database). It keeps running in this terminal until you
press Ctrl-C:

```bash
LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000
```

In a second terminal, from the repository root, start the web app:

```bash
npm --prefix frontend ci && npm --prefix frontend run dev
```

Sign in at http://localhost:5173 with the printed token. From there, use
Admin → User accounts to create further accounts and Admin → Members &
roles to grant them roles on a matter — see
["Provisioning users & access"](#provisioning-users--access) below for the
full flow. The rest of this runbook is the manual, step-by-step breakdown
of what bootstrap and the demo seed each automate.

**Upgrading later.** After pulling a newer LexGraph, run
`.venv/bin/python -m app.migrate --db dev.db` (from `backend/`) before
starting the server. It changes nothing when there is nothing to upgrade, and
the server refuses to start on an out-of-date database until it has run. See
["Upgrading an existing database"](#upgrading-an-existing-database-migration).

### Optional: demo workspace (local testing / mockup data)

`./scripts/demo.sh` is a local-testing convenience, not a provisioning
path — it seeds a demo workspace into `backend/dev.db` with fixed,
hardcoded accounts and starts backend (:8000) + frontend (:5173) in one
command. Ctrl-C (or SIGTERM) stops both servers:

```bash
./scripts/demo.sh
```

- **Settings.** `BACKEND_PORT` (default 8000), `FRONTEND_PORT` (default 5173) and `DEMO_DB` (default `backend/dev.db`, relative to the repository root), for example `DEMO_DB=backend/demo.db BACKEND_PORT=8001 FRONTEND_PORT=5174 ./scripts/demo.sh`. The web app's `/api` proxy always points at the demo's own backend port.
- **It fails instead of guessing.** A port that is already in use, or a server that exits while starting, stops the demo with an error naming the cause; it never moves to another port or talks to another program's server. If either server stops later, the other one is stopped too.
- **It only uses a demo database.** An existing `DEMO_DB` file is upgraded with `app.migrate` only when it holds the demo users. A workspace from `app.bootstrap`, or any other file, is refused and left unchanged; use another `DEMO_DB` for the demo. An empty file is replaced by the demo.
- **Running it again completes an interrupted first run.** It reinstalls the backend when `backend/.venv` cannot import the app, runs `npm --prefix frontend ci` when `frontend/node_modules` is incomplete or out of date with `package.json`, and seeds into a scratch directory that it moves into place only when the seed has finished.

Sign in at http://localhost:5173 with the demo sign-in token `admin`,
`reviewer`, `contributor`, or `viewer` (no admin action created these;
they're fixtures for exercising the UI locally). Each demo token is also
that account's public user id, so anyone can sign in as any demo account:
the server logs a legacy-credential warning at startup and the admin
console badges them "Legacy sign-in". Never use the demo seed for real
data. The seeder
(`backend/app/seed_demo.py`) drives the real API, so the demo data carries
genuine revisions, ratings, comments, audit events and the notifications
those actions raised (stored in the database like any others: the admin,
reviewer and contributor bells start with unread notifications, the viewer's
is empty) — useful for development and mockups, not for a real deployment.

### Backend Environment Setup

Initialize the backend virtual environment and install dependencies, from the repository root (the Quickstart's first command):

```bash
(cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')
```

### Frontend Environment Setup

The web app's toolchain (Vite 8, Vitest 5) needs Node.js 22 (22.12 or later) or 24; CI uses 24. Install frontend dependencies:

```bash
npm --prefix frontend ci
```

## Database Setup

### Initialize the Database

LexGraph stores everything in one SQLite database file; it supports no other database yet. The server, the agent CLI, the offline pipelines and the MCP server read its location from the same environment variable, and so do `app.bootstrap`, `app.migrate` and `app.rotate_sign_in_token` unless `--db PATH` names the file. `app.seed_demo` is the exception: it ignores the variable and writes the file given by `--db` (default `dev.db` in the current directory), so pass the same file to it. This runbook uses `backend/dev.db`, the file the Quickstart bootstraps. Set the variable from the repository root:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
```

`$PWD` makes it the absolute, four-slash form, which names the same file from any directory. A relative URL such as `sqlite:///dev.db` resolves against the directory each command runs in. The commands below that start with this `export` run from the repository root; use another file name throughout for another database.

Leaving the variable unset selects an in-memory database. No other process can fill it, so the server and the agent tools refuse to use it.

### Database Schema

The backend does **not** create the schema itself (`create_app()` never calls `Base.metadata.create_all()`; `python -m app.bootstrap` does, together with the first admin). At startup the server checks the database against the current models. It refuses to start, printing what is wrong and the exact command to run, when:

- the database file does not exist or has no LexGraph tables. Create the workspace with `python -m app.bootstrap --db PATH` (Quickstart). The check never creates the missing file.
- the database was created by an older LexGraph and lacks tables, columns or unique indexes the code needs. Upgrade it with `python -m app.migrate --db PATH` (see "Upgrading an existing database" below).
- `LEXGRAPH_DATABASE_URL` is unset (in-memory).

It never starts "healthy" on a database it would answer HTTP 500 for. The one index it does without is the unique email index while accounts still share an address: the server then starts and logs a warning naming them (see "Upgrading: case-insensitive emails"). The agent CLI and the MCP server run the same check before they open the database.

To create an empty schema without bootstrap's first organization, matter and admin (one-time step for a new file-backed database), with `LEXGRAPH_DATABASE_URL` exported as above:

```bash
cd backend
.venv/bin/python -c "
import app.models  # register ORM mappings
from app.config import get_settings
from app.db import Base, make_engine

Base.metadata.create_all(make_engine(get_settings().database_url))
"
cd ..
```

### Upgrading an existing database (migration)

After pulling a newer LexGraph, upgrade every existing database file before you start the server. One command applies every pending schema migration:

```bash
cd backend
.venv/bin/python -m app.migrate --db dev.db
# or, reading the same variable the server uses:
LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/python -m app.migrate
```

It prints one line per migration and then checks the result against the current models. On a workspace provisioned on 2026-07-31:

```text
Upgrading /path/to/LexGraph/backend/dev.db
  20260726_add_raw_text_columns                    already applied
  20260729_add_definition_link_tables              already applied
  20260802_add_document_jurisdiction_column        applied
  20260804_add_assertion_subject_unit_path_column  applied
  20260805_add_heading_breadcrumbs_column          applied
  20261116_assertion_comments_index                applied
  20261116_assertion_read_indexes                  applied
  20261116_assertion_revision_number_unique        applied
  20261116_backfill_initial_assertion_revisions    already applied
  20261116_durable_notifications                   applied
  20261116_revision_reason_raw                     applied
  20261116_sign_in_tokens                          applied
  20261116_users_email_unique                      applied
Applied 10 of 13 migrations; the schema is current.
```

- **Safe to re-run.** Every migration changes only what is missing. On a current database the command changes nothing and ends with `Nothing to do: all 13 migrations were already applied; the schema is current.` Run it after every upgrade, and point it at the same file the server uses.
- **One transaction per migration.** On SQLite the runner makes `ALTER TABLE` transactional too, so a migration that fails is rolled back completely. The run stops there and exits 1; migrations applied before it are kept. Fix the cause and run the same command again.
- **It never creates or empties a database.** A missing file, or a file without LexGraph tables, is refused with exit status 1 and a pointer to `python -m app.bootstrap`. Migrations add tables, columns and indexes and fill in missing values; they never delete or merge rows. Copying the file first (`cp dev.db dev.db.bak`) is still cheap insurance.
- **Some steps need an operator.** When stored rows stand in the way of a unique index (accounts sharing an email address), the migration leaves that index out and changes none of those rows. The run still exits 0, marks the migration `waiting for an operator` and ends by naming the rows and what to do. The server serves such a database meanwhile. Resolve them and run the command again (see "Upgrading: case-insensitive emails").

The migrations shipped so far, in the order they run (`backend/app/migrations/`; every new migration adds a row here):

| `MIGRATION_ID` | Schema change | Existing rows |
|---|---|---|
| `20260726_add_raw_text_columns` | `proposition_raw`, `comment_text_raw`, `rationale_raw` columns | backfilled from the sanitized text (see below) |
| `20260729_add_definition_link_tables` | `articles` and `definitions` tables (definition linking) | none: new, empty tables |
| `20260802_add_document_jurisdiction_column` | `documents.jurisdiction` (`NOT NULL DEFAULT 'IL'`) | every existing document becomes `IL` (all pre-2026-08-02 documents are Israeli law) |
| `20260804_add_assertion_subject_unit_path_column` | `assertions.subject_unit_path` | `NULL` (no sub-article path known) |
| `20260805_add_heading_breadcrumbs_column` | `articles.heading_breadcrumbs` | `NULL` (no breadcrumbs captured) |
| `20261116_assertion_comments_index` | index on `assertion_comments (assertion_id)`, which an assertion's discussion and the recipients of every comment, evidence and edit notification are read by | none: an index only. The server starts without it; without it each comment, evidence or edit request scans every matter's comments |
| `20261116_assertion_read_indexes` | indexes on `assertions (matter_id, status)`, `assertion_evidence (assertion_id)`, `assertion_ratings (assertion_revision_id)` and `audit_events (assertion_id, event_type)`, which the list, detail page, graph and statistics read by | none: indexes only. The server starts without them; they make large matters fast |
| `20261116_assertion_revision_number_unique` | unique index on `assertion_revisions (assertion_id, revision_number)` | a revision number that concurrent edits stored twice is renumbered first, never deleted: the row matching the assertion's current text becomes the newest, later numbers move up, ratings stay with the row they rated, and each move is logged as a warning |
| `20261116_backfill_initial_assertion_revisions` | none | an assertion stored without revision 1 (definition-link output written before 2026-11-16) gets it, plus an `assertion_created` audit event marked `migration:<id>`; one edited before then keeps only its later revisions, because the original text was not stored |
| `20261116_durable_notifications` | `notifications` and `notification_preferences` tables | none: notifications raised before the upgrade lived only in the old server process |
| `20261116_revision_reason_raw` | `assertion_revisions.revision_reason_raw` | `NULL`: a reason saved before keeps its stored text and has no separate raw copy |
| `20261116_sign_in_tokens` | `users.sign_in_token_hash` and its unique index | every existing account gets a legacy token equal to its user id (see "Upgrading: sign-in tokens replace user-id sign-in") |
| `20261116_users_email_unique` | unique index `ix_users_email` | stored addresses are lowercased; accounts that share one are reported and left for an operator (see "Upgrading: case-insensitive emails") |

The individual modules stay importable and are idempotent, so the older per-module command (for example `from app.migrations.add_raw_text_columns import upgrade; upgrade(engine)`) still works. `python -m app.migrate` is the supported path: it applies them in order, makes each one atomic, and verifies the result.

Effective dates are stored as UTC instants from 2026-11-16 on. Before that, a date submitted with a UTC offset (for example `2030-01-01T00:00:00+05:00`) was stored as its wall-clock part with the offset dropped. The offset is not recorded anywhere, so no migration can correct such values; an edit that leaves both dates alone still works, and resubmitting a date stores it correctly. Ranges that became inverted this way can be listed with `SELECT id FROM assertions WHERE effective_to < effective_from;`.

**Adding a migration (developers).** A schema change that existing databases need ships as a new module `backend/app/migrations/m<YYYYMMDD>_<slug>.py` with `MIGRATION_ID = "<YYYYMMDD>_<slug>"` and an idempotent `upgrade(engine) -> bool`. The ORM models must declare the same schema, because fresh databases are still built by `create_all()`. The runner picks the module up automatically. The binding rules are in `backend/app/migrations/__init__.py`, and `backend/tests/integration/test_migrate_runner.py` checks every module against real historical schemas (`backend/tests/fixtures/schema_history/`).

### Backfill: Historical Rows

The raw-text migration (`20260726_add_raw_text_columns`) adds three new columns:
- `proposition_raw` in `assertion_revisions`
- `comment_text_raw` in `assertion_comments`
- `rationale_raw` in `assertion_ratings`

For any existing database with rows created before this upgrade, the migration automatically backfills these raw columns from their sanitized counterparts. This means historical rows will contain the sanitized approximation of the text, not the original bytes, because the original raw text is no longer available at the time of migration. New rows created after the migration will store both the original raw text and the sanitized version.

If you need to downgrade and remove these columns (to go back to a LexGraph version that predates them; the current server refuses to start without them until you run `python -m app.migrate` again), run, with `LEXGRAPH_DATABASE_URL` exported as in "Initialize the Database":

```bash
cd backend
.venv/bin/python -c "
from app.migrations.add_raw_text_columns import downgrade
from app.db import make_engine
from app.config import get_settings

settings = get_settings()
engine = make_engine(settings.database_url)
downgrade(engine)
"
cd ..
```

## Backend Server

### Starting the Backend

Start the FastAPI backend server:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
cd backend
.venv/bin/uvicorn app.main:app --port 8000
```

The backend will be available at `http://localhost:8000`. Check the health status with:

```bash
curl http://localhost:8000/healthz
```

**Keep the backend on this machine.** uvicorn listens on `127.0.0.1` unless told otherwise, so only programs on this computer can reach it, and every command in this runbook keeps that default. Do not add `--host 0.0.0.0`: it serves `/api/v1`, `/docs` and `/openapi.json` on every network interface over plain HTTP, and LexGraph's sign-in is built for a trusted local installation, not for a network. On the demo workspace, for example, the credentials are the role names themselves (`admin`, `reviewer`, …). To use LexGraph from another computer, leave the bind as it is and connect through an encrypted, authenticated channel instead, such as an SSH tunnel started on that computer:

```bash
ssh -N -L 8000:127.0.0.1:8000 you@lexgraph-host
```

Then open `http://localhost:8000` on that computer, with the web app built so that the backend serves it (see "Serving the web app in production"). For a team, run a reverse proxy on the LexGraph host that terminates HTTPS and restricts who may connect, and point it at `http://127.0.0.1:8000`.

If the database cannot be served (see "Database Schema" above), uvicorn exits during startup with status 3, before binding the port. The end of its output names what is missing and the command that fixes it, for example on a workspace provisioned on 2026-07-31:

```text
app.migrate.SchemaNotCurrentError: LexGraph cannot start: the database at /path/to/LexGraph/backend/dev.db was created by an older version of LexGraph. It is missing:
  - table notification_preferences
  - table notifications
  - column users.sign_in_token_hash
  - column assertions.subject_unit_path
  - column documents.jurisdiction
  - column articles.heading_breadcrumbs
  - unique (email) on users
  - unique (sign_in_token_hash) on users
  - unique (assertion_id, revision_number) on assertion_revisions
Upgrade it in place (safe to re-run; each migration runs in its own transaction):
    /path/to/LexGraph/backend/.venv/bin/python3 -m app.migrate --db /path/to/LexGraph/backend/dev.db

ERROR:    Application startup failed. Exiting.
```

Run the printed command, then start the server again.

### Backend REST API

The backend provides REST APIs at `/api/v1/` for managing assertions, comments, ratings, and the graph. The backend serves its own interactive API documentation. It works with no internet connection: Swagger UI and Redoc are bundled in `backend/app/static/api-docs/`, refreshed with `scripts/vendor_api_docs.sh`.

- `http://localhost:8000/docs` (Swagger UI): click **Authorize** and paste your sign-in credential, the same value you enter on the web app's sign-in page. **Try it out** then sends it as `Authorization: Bearer <credential>` with every call. The credential is kept in the browser's local storage across reloads until you click **Logout** in the same dialog.
- `http://localhost:8000/redoc` (Redoc): read-only reference.
- `http://localhost:8000/openapi.json`: the OpenAPI 3.1 schema. It declares the bearer scheme (`HTTPBearer`) for every operation except `/healthz`, and documents the 401 each one returns without it.

Both pages load files from the backend only. Their Content-Security-Policy makes the browser refuse any third-party request, including the attribution logo Redoc would otherwise fetch from its CDN.

`GET /api/v1/assertions?matter_id=<id>` accepts the search, filter and sort parameters listed in [the spec](specs/collaborative-assertions.md#listing-statistics-graph-bounds-and-timestamps-2026-11-16) and pages with `limit` (1–500) and `offset`. `total` in the response always counts every match. Without `limit` every match is returned, which can be tens of megabytes for a matter holding pipeline output, so scripts should page. Unknown query parameters and sort keys return 422. `GET /api/v1/matters/<id>/graph` returns at most `limit` edges (default 1000) together with `total`, and `GET /api/v1/matters/<id>/assertion-stats` returns matter-level counts. Every timestamp the API returns is UTC with an explicit offset; `effective_from`/`effective_to` are calendar dates without one.

### Offline Pipelines (CLI-only, no frontend UI)

Two deterministic, offline batch passes run against a matter's already-stored data and write draft/accepted assertions directly to the database (no LLM/network calls). Both read `LEXGRAPH_DATABASE_URL` the same way the backend server does, so point them at the same database file the server uses.

**Enrichment** (`app/enrich/`) suggests candidate assertions from existing `SourceSpan` rows:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
cd backend
.venv/bin/python -m app.enrich.cli --matter-id <matter-id> --triggered-by-user-id <user-id>
cd ..
```

Each suggestion is a `draft`, `model_suggested` assertion authored by `--triggered-by-user-id`, which must be an existing user with a contributor, reviewer or admin role in the matter. The CLI prints `enrichment failed: ...` and exits 1 when that user is unknown or has no such role, and likewise for an unknown matter, an unset or in-memory `LEXGRAPH_DATABASE_URL`, a database file that does not exist (the message names the resolved path; nothing is created), a database without the LexGraph tables, or one an older LexGraph created (it names the `python -m app.migrate` command): the same database check the agent CLI runs. Rerunning it is idempotent: it skips spans it has already suggested from, never suggests the same proposition twice in a matter (two spans with one text give one draft, also after that draft is withdrawn or rejected), and does not store an exact duplicate of a live assertion or of the triggering user's own draft. Agent submissions share the `model_suggested` origin, but enrichment's rows are the ones whose revision 1 has the reason `model-suggested (offline enrichment)`. A span an agent or lawyer has cited is therefore still suggested. A span of up to 1,000 characters is suggested whole; from a longer one, such as an ingested statute section, the suggestion quotes the sentence that matched, and a match that cannot be quoted within 1,000 characters is skipped. Drafts suggested before 2026-11-16 from such spans keep the whole section as their proposition, and a rerun does not replace them because their spans count as suggested; list them with `SELECT a.id FROM assertions a JOIN assertion_revisions r ON r.assertion_id = a.id AND r.revision_number = 1 WHERE r.revision_reason = 'model-suggested (offline enrichment)' AND length(a.proposition) > 1000;` and withdraw or edit them.

**Definition linking** (`app/definition_links/`, sprint 2026-07-29-definition-links) deterministically (regex/rule-based, no LLM/ML) connects articles within a law to the definitions the law contains, and connects laws to each other when a definition explicitly derives from another law (e.g. "כהגדרתו בחוק..."). It requires `Article` rows already ingested via `app.definition_links.ingest.ingest_wiki_law` (there is no ingestion CLI yet — call `ingest_wiki_law(session, ...)` directly, e.g. from a one-off script or a REPL, to load a `.wiki`-formatted law's text into `Document`/`Article`/`SourceSpan` rows for a matter):

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
cd backend
.venv/bin/python -m app.definition_links.cli --matter-id <matter-id> --triggered-by-user-id <user-id>
cd ..
```

This writes `USES_DEFINITION` (an article uses a term defined elsewhere in the same law) and `DERIVES_FROM_LAW` (a definition explicitly derives from another law) assertions with `origin=system_generated`, `status=accepted`. An unresolved cross-law derivation (the target law was never ingested into this matter) is still recorded, with a null object entity and the raw matched law-reference text preserved in the proposition — never dropped, never a fabricated resolution. An article whose text shows reversed-word-order (bidi-degraded) artifacts is flagged and skipped, never auto-corrected. Each assertion is stored with revision 1 (its generated proposition) and an `assertion_created` audit event naming the triggering user, so it can be rated and its original text survives an edit; it carries no evidence rows yet. On a database linked before 2026-11-16, `python -m app.migrate` adds the missing revision 1 (migration `20261116_backfill_initial_assertion_revisions`). The pass is idempotent — rerunning it over unchanged articles creates no additional rows. Results are visible via the existing `GET /api/v1/assertions?matter_id=<id>&origin=system_generated` endpoint (no dedicated route or frontend UI this sprint); add `&limit=100&offset=<n>` to page through a large run.
The assertion detail page, the Review Queue and Contested show these rows as pipeline-generated: the pipeline is the author, the `--triggered-by-user-id` user is named only as the user the run is attributed to, and the evidence badge reads "System-derived".

### Ingesting US statutes (`vaquill/open-us-law` dataset)

Sprint 2026-08-02-us-state-law (item 5, gate G6) adds an ingester for the
[`vaquill/open-us-law`](https://huggingface.co/datasets/vaquill/open-us-law)
Hugging Face dataset of US statutes and constitutions (50 states, DC, PR and
federal; about 2M statute sections when LexGraph was built against it). The
dataset has changed since: read "Getting the dataset" below before you
download it. `pyarrow` is a real backend dependency (see
`backend/pyproject.toml`), so the backend install in "Backend Environment
Setup" above already installs it.

Each Parquet file is ingested with **one command**, which creates one
`Document` (using `--title`) and one `Article` + `SourceSpan` per row:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
cd backend
.venv/bin/python -m app.definition_links.ingest_us_statutes_cli \
    --input /path/to/us_de_statutes.parquet \
    --repository-id <repository-id> \
    --matter-id <matter-id> \
    --title "Delaware Code -- Statutes" \
    --jurisdiction US-DE
cd ..
```

`--jurisdiction` must be one of the controlled-vocabulary codes served at
`GET /api/v1/jurisdictions` (e.g. `US-DE`, `US-CA`, `US-DC`, `US-PR`,
`US-FED`) — an unrecognized code fails the command rather than silently
tagging the wrong jurisdiction. The file is streamed in row-group batches
(`--batch-size`, default 5000) rather than loaded into memory all at once,
so it scales to the dataset's largest state files; progress (rows newly
ingested / matched (already ingested) / skipped per batch) prints as it
runs. A row missing its `text` or `act_id` column is skipped and reported,
not fatal to the rest of the file. The command is resumable/idempotent —
re-running it against the same file reuses the same `Document` and does not
duplicate `Article`/`SourceSpan` rows for sections already ingested — and
exits non-zero for a missing/unreadable input file.

Idempotency is keyed on the dataset's own per-row `act_id` (verified 100%
unique across all 570,397 real rows sampled from 10 real state files,
including the two largest checked, `us_ca_statutes.parquet` at 161,429 rows
and `us_pa_statutes.parquet` at 14,547 rows) — not on any combination of
`section_number`/`section_title`/`text`, which real cross-title boilerplate
can make byte-identical for two genuinely different sections (see
`ingest_us_statutes.py`'s module docstring for the full collision history).

**Ingesting a whole downloaded corpus (gate G6) is ONE command** using
`--input-dir` instead of `--input` — bulk directory mode, not a shell loop
around the single-file command. Point it at the directory holding the
downloaded statutes and constitutions files:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
cd backend
.venv/bin/python -m app.definition_links.ingest_us_statutes_cli \
    --input-dir /path/to/open-us-law \
    --repository-id <repository-id> \
    --matter-id <matter-id>
cd ..
```

Bulk mode derives BOTH `--title` and `--jurisdiction` per file from its own
filename — the dataset's own `us_<postal-or-federal>_<statutes|
constitutions>.parquet` naming (e.g. `us_de_statutes.parquet` → title
`us_de_statutes`, jurisdiction `US-DE`; `us_dc_constitutions.parquet` →
`US-DC`; `us_federal_statutes.parquet` → `US-FED`) — validated against the
same controlled vocabulary as single-file mode before that file is touched.
Files are processed in sorted filename order, **one at a time, in the same
process**. Critically, **a single file failing (corrupt/unreadable input, a
filename that doesn't match the naming convention, an unrecognized derived
jurisdiction code) is recorded and the run CONTINUES to the next file** —
it never aborts the whole run over one bad file. A final summary
prints files found/processed/failed (with each failure's reason), total
rows newly ingested, total rows matched (already ingested — i.e. a
re-ingested `act_id`, reported SEPARATELY from newly-created rows so a
same-batch collision or a partial re-run cannot hide inside a single
combined count), and total rows skipped broken down by reason — the real
measured report the corpus-scope decision asks for. The process exits
non-zero if any file failed, so the run is still scriptable, without ever
giving up on the remaining files. Bulk mode is resumable the same way
single-file mode is: re-running the same `--input-dir` command reuses every
already-ingested `Document`/`Article`/`SourceSpan` and creates no
duplicates — a file that failed partway through a previous run just needs
the whole `--input-dir` command run again (or can be re-run alone with
single-file `--input` pointed at just that one file, using the same
`--jurisdiction`/`--title` its filename derives to).

#### Getting the dataset

The `.venv/bin/python` process itself never downloads the dataset: fetch the
Parquet files into one local directory first, and point `--input-dir` (or
`--input` for a single file) at it. As checked on 2026-11-16, the dataset has
changed in three ways since LexGraph was built against it in 2026-08:

- **It is gated.** Anonymous downloads are refused: the Hub answers HTTP 401,
  and the Hugging Face CLI prints `Access denied. Dataset
  'vaquill/open-us-law' requires approval.` Sign in at huggingface.co,
  request access on the dataset page, then download with an access token.
- **Its files are different.** The current revision (`eed1dd8c…`, updated
  2026-10-07) has 313 files: 48 statutes files (none for Arkansas, Colorado,
  Georgia, Mississippi or Tennessee), 51 constitutions files, and 209 Parquet
  files of other kinds (regulations, court rules, attorney-general opinions,
  guidance and more). LexGraph's US definition linking was certified on
  revision `301000fc3465374ee0f23c3c6953a8a861e95cad`, which had a statutes
  file for each of the 53 jurisdictions (2,038,247 rows). The Hub no longer
  serves that revision (see "Re-certifying US definition linking" below).
- **Its license tag changed** from `cc-by-4.0`, recorded when the sprint
  reviewed the dataset, to `cc-by-nc-4.0` (non-commercial). Read the dataset
  card before you use it.

Bulk mode takes statutes and constitutions files only. It records every other
file in `--input-dir` as failed (`filename does not match ...`) and exits 1, so
download just those two kinds. For example, with the Hugging Face CLI (`hf`,
from the `huggingface_hub` package 0.34 or later, installed in any Python
environment; it is not a LexGraph dependency), after `hf auth login` with your
token, run one command per kind into the same directory:

```bash
hf download vaquill/open-us-law --repo-type dataset \
    --include 'us_*_statutes.parquet' --local-dir /path/to/open-us-law
hf download vaquill/open-us-law --repo-type dataset \
    --include 'us_*_constitutions.parquet' --local-dir /path/to/open-us-law
```

Give each command one `--include` with one pattern. Before huggingface_hub 1.0
(`hf version` prints yours) a second `--include` replaces the first, so a single
command fetches only the constitutions and still exits 0; from 1.0 on, a second
pattern after one `--include` is taken as a file name. Bulk mode also exits 0 on
a directory without the statutes, so count the files before you ingest: at
revision `eed1dd8c…`, `ls /path/to/open-us-law/us_*_statutes.parquet | wc -l`
prints 48, and the same for `us_*_constitutions.parquet` prints 51.

#### Re-certifying US definition linking

The US definition-linking rules were certified against one fixed copy of the
corpus: the statutes files of revision
`301000fc3465374ee0f23c3c6953a8a861e95cad` (53 files, 2,038,247 rows). The
certification harness in `docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/`
(procedure in its `G7_CERTIFICATION.md`) refuses any other copy: the snapshot
directory must be named for that revision and hold exactly that many files and
rows. Only a change to the code a certification run measures calls for a new
run: the files and symbols that `qa_g7_common.MEASURED_PRODUCTION_PATHS` and
`MEASURED_SHARED_SYMBOLS` declare (`backend/app/definition_links/`, the
jurisdiction vocabulary, two package `__init__.py` files and the
`ValidationError` class), checked by
`backend/tests/unit/test_certification_freeze_scope.py`. Other backend
changes need no re-certification.

As of 2026-11-16, no certification run is possible from a clean checkout:

- **The pinned revision is gone from the Hub.** The Hub's revision API answers
  `404 Invalid rev id` for `301000fc…`, as it does for a made-up id, while it
  still resolves the current head and other refs of the same gated dataset
  for anonymous callers. The repository records no checksums of the snapshot's
  files (the harness checks the directory name, file count, columns and row
  count only), so a run needs an existing local copy, such as the Hugging Face
  cache of the machine that certified it.
- **The recorded runner scripts only work on that machine.** `run_g7_repin.sh`
  and `run_gate2.sh` (in the `2026-08-12-defs-b1-refers-to-scripts/` and
  `2026-08-20-defs-boundary-idioms-scripts/` sprint directories) and the
  commands in `G7_CERTIFICATION.md` hard-code its interpreter and snapshot
  paths (`/Users/nerya/...`). Anywhere else the scripts stop at once with exit
  status 127, and they read neither path from the environment, so run copies
  edited to use your own `backend/.venv/bin/python` and snapshot path. The
  harness itself needs nothing more: pointed at a copy with the wrong name or
  file count, it fails closed with a `CertificationError`.
- **The current revision cannot simply replace it.** It has no Georgia
  statutes file, but certification fails unless the Georgia count
  (`US-GA after`) reaches 2,794, and four more states are missing. The file
  and row counts, every summary hash and the D-PFP-400 sample would all
  change, so moving to a newer revision is a new certification with new
  targets, which has to be decided before any run.

### Getting sources into a matter

Every assertion is anchored to a document or article of its matter and cites
that matter's source passages as evidence, so a matter needs imported sources
before anyone can suggest assertions in it. A freshly bootstrapped matter has
none; its **Suggest Assertion** page then explains this and shows the matter
and repository IDs instead of the form. Sources cannot be uploaded through the
web app or the REST API: an administrator imports them on the server, into the
database file the backend serves (same `LEXGRAPH_DATABASE_URL`):

- **US statutes** (Parquet files of the `vaquill/open-us-law` dataset): run
  `app.definition_links.ingest_us_statutes_cli` as shown in "Ingesting US
  statutes" above, with `--matter-id` and `--repository-id` of the target
  matter. Each file becomes one document with one article and one source
  passage per row.
- **Laws in `.wiki` format** (the Hebrew corpus): there is no command yet; call
  `ingest_wiki_law` from a short Python script run in `backend/`:

  ```python
  from pathlib import Path
  from sqlalchemy.orm import Session
  from app.config import get_settings
  from app.db import make_engine
  from app.definition_links.ingest import ingest_wiki_law

  with Session(make_engine(get_settings().database_url)) as session:
      ingest_wiki_law(session, repository_id="<repository-id>", matter_id="<matter-id>",
                      title="<law title>", wiki_text=Path("<law>.wiki").read_text(encoding="utf-8"))
  ```

  It stores one document plus an article and a source passage per parsed
  article, and commits.

The matter and repository IDs are shown on the empty **Suggest Assertion**
page and returned by `GET /api/v1/me`. Imported documents and articles appear
in the page's source pickers at once (use **Check again** on the empty page,
or reload). The demo seed (`app.seed_demo`) creates its own sample documents
for local testing only.

## Web Application

### Starting the Web App

In a separate terminal, start the Vite development server:

```bash
npm --prefix frontend run dev
```

The app will be available at `http://localhost:5173` (or the port specified by Vite); the dev server proxies `/api` to `http://127.0.0.1:8000` (override with `LEXGRAPH_API_PROXY`). Sign in with your sign-in token (bootstrap prints the first admin's; the admin console shows each new account's once; `backend/app/auth.py`). Your user id is not a sign-in token. With the demo seed the tokens are `admin`, `reviewer`, `contributor`, and `viewer`.

The browser remembers your sign-in. Only the server rejecting your token
(it was rotated or revoked) signs you out, with a message saying so. If
the app cannot reach the backend when you open it (backend not started
yet, restarting, or a proxy error), it keeps your sign-in and shows
**Retry** instead of the sign-in page; it also retries by itself when
the browser comes back online or the tab regains focus. While you work,
the app re-reads your account (`GET /me`) when a request is refused,
when you return to the tab, and every minute, so a role another admin
gave you or took away shows up without a reload. Each tab keeps the
matter you chose in it; a new tab, or a reload, opens on the matter you
chose last. Signing out in one tab signs out the browser's other tabs
too, and when one tab finds that your token no longer works, the others
show the sign-in page with the same message. On a narrow screen
(below 768px wide) the sidebar is behind the menu button at the top
left.

The UI implements the Consensus design system (see [docs/design/consensus-ui-review.md](design/consensus-ui-review.md)):
- **Review Queue** — proposed assertions with strength-rating summaries; reviewers accept/reject/dispute/request revisions
- **Knowledge Base** — the matter's accepted assertions by default (the Status filter shows any status), 50 rows per page, sortable by rating (user opinion, not legal authority); CSV export downloads every match, in the table's order, as UTF-8 with a byte-order mark (Excel opens it directly, Hebrew included; a program reading it should decode `utf-8-sig`), with spreadsheet formula triggers (`=`, `+`, `-`, `@`, tab, carriage return) neutralized by a leading apostrophe. Assertions reviewed, edited or rated while it runs never make it skip one that matches the whole time, and never put a line out of order (one that starts matching meanwhile is either in its place or left out); if very many change at once it starts over, and if that happens three times it fails and says so rather than download part of the list. The topbar search opens it on all statuses, and submitting the same query again re-runs it
- **Suggest Assertion** — contributor submission flow with evidence spans and duplicate warnings
- **Assertion detail** — evidence (attach and remove, under the edit rule), threaded comments (reply; edit or delete your own), review history, revision history with a side-by-side comparison of any two revisions, ratings with rationales, and role-gated review actions, including superseding an accepted assertion
- **Contested** — adjudication queue for disputed assertions
- **Analytics** — per-matter dashboard computed live by the server (`GET /api/v1/matters/<id>/assertion-stats`), with weekly counts in your timezone
- **Admin** — user account provisioning and matter member/role management (admin role required)
- **Profile** — your activity (counts from the same statistics; your suggestions and the proposed assertions awaiting your rating, 50 at a time), all your notifications (50 at a time, with your unread count), and matters

### Notifications

The bell in the top bar shows whether you have unread notifications (its
label gives the count). Each notification names the assertion, who acted and
in which matter. Opening one marks it read and takes you to the assertion,
switching to its matter first when needed; **Mark all as read** marks
every notification up to the newest one listed (one that arrives meanwhile
stays unread). The bell lists your 20 newest notifications. The Profile
page's **Notifications** tab lists all of them, 50 at a time (**Show more**
loads older ones), with the same actions; the tab and the line above the
list give your unread count, which includes notifications not loaded yet.
The gear in the bell's panel chooses which events notify you.

| Event | Who is notified |
|---|---|
| An assertion enters review: created as proposed (Suggest Assertion's **Submit for review**, `POST /api/v1/agent/assertions`, the agent CLI's `suggest`, the MCP `suggest_assertion` tool), submitted from draft, or resubmitted after a revision request | The matter's reviewers and admins |
| Revision requested, accepted, rejected, disputed or superseded | The assertion's author |
| New revision, evidence added | Everyone who has worked on the assertion (author, editors, evidence contributors, commenters, raters, last reviewer), plus the matter's reviewers and admins while it awaits review |
| Comment added | Everyone who has worked on the assertion, and the author of the comment replied to |
| A rating added or changed | The author, only after they switch this on (off by default) |

Nobody is notified about their own action, and only current members of the
matter are notified; a notification's assertion text and link are hidden
from a recipient who has since lost access to the matter. Re-submitting an
assertion that is already proposed, or repeating a decision that changes
nothing, does not notify anyone again. Notifications are stored in the
database (tables `notifications` and `notification_preferences`), so they
survive restarts and every API worker serves the same feed; they are not
deleted automatically. The agent CLI and the MCP server write to the same
tables, so their proposals notify the reviewers too.

The API is `GET /api/v1/notifications` (newest first; `limit` 1–200, default
50, `offset`, `unread_only`), `GET /api/v1/notifications/unread-count`,
`POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/read-all`
(optional body `{"last_read_at": "<ISO 8601>"}`: newer notifications stay
unread) and `GET`/`PUT /api/v1/notifications/preferences`
(`{"preferences": {"comment_added": false}}`). Each route acts on the
caller's own notifications only.

**Upgrading an existing database.** Databases created before notifications
were stored lack the two tables, so the server refuses to start on them until
`python -m app.migrate` has created them (migration
`20261116_durable_notifications`; see "Upgrading an existing database").
Notifications raised before the upgrade lived only in the old server process,
so there are none to carry over.

### Provisioning users & access

Once signed in as an admin (bootstrap prints the first one — see
["Quickstart"](#quickstart-real-provisioning) above), provisioning further
people is entirely in-app; no CLI or DB access is required:

1. **Create the account.** Admin → **User accounts** → fill in email and
   display name → **Create account**. Email addresses are
   case-insensitive: they are stored in lowercase, and an address another
   account already uses (in any letter case) is refused. The page shows the new account's
   **sign-in token** once, with a copy button: copy it and hand it to the
   person privately, then click **Done**. It cannot be shown again (only a
   hash is stored); if it is lost, rotate it (below). The user id in the
   table is a public reference, not a credential. Creating an account
   pre-fills its email into the Members & roles add-member field so
   granting access is the very next step.
2. **Grant matter access.** Admin → **Members & roles** → the new
   account's email is already filled in → pick a role (viewer,
   contributor, reviewer, or admin) → **Add**. Roles are per-matter: the
   same account can be a reviewer on one matter and have no access to
   another, and admin is a per-matter admin, not a global superuser role
   (any admin-of-some-matter can list/create user accounts, per the users
   API's access model). The email is matched case-insensitively. A matter
   always keeps at least one admin, even when two admins demote each other
   at the same moment. Changing your own role or removing yourself takes
   effect in your browser at once: the app leaves the admin console and
   shows your new access.
3. **They sign in.** The new user enters the token from step 1 on the
   sign-in page and immediately sees the UI appropriate to the role(s)
   they were granted.

This replaces hand-editing the database or re-running the demo seed for
real usage — the seed stays a local-testing convenience (see "Optional:
demo workspace" above), never the provisioning path for an actual
deployment.

### Sign-in tokens, rotation and lockouts

Every account signs in with its own random sign-in token. The backend
stores only its SHA-256 hash and never returns a token except once, when
it is issued: by bootstrap, by **Create account**, or by a rotation. Tokens
are bearer secrets and the backend speaks plain HTTP, so keep it on
localhost or put TLS in front of it before exposing it on a network.

- **Rotate or re-issue in the app.** Admin → **User accounts** → **Rotate
  token** (or **Issue token** for an account without one) → confirm. The
  new token is shown once and the previous one stops working immediately:
  that person's open sessions are signed out, with a message saying the
  saved token is no longer valid, as soon as one of their tabs notices
  (their next refused request, their return to the tab, or within a
  minute; that browser's other tabs follow at once), and they sign in with
  the new token. You may
  rotate an account only
  if you are an admin on every matter it belongs to (or it is your own
  account; rotating your own keeps this browser signed in, even if you
  leave the page before the server answers, and the new token is then
  shown once at the top of whatever page you are on, until you click
  **Done**. If you sign out before that, in that tab or another, the
  browser stays signed out and that tab's sign-in page shows the new
  token instead, so you can still save it and sign in with it. If it is
  rotated again meanwhile, by another admin or in another browser, the
  page stops showing it once signing in with it is refused or you sign
  in with the newer token).
- **Lockouts (no admin can sign in).** With access to the database file,
  issue a new token from the command line. It prints the token once:

  ```bash
  cd backend
  .venv/bin/python -m app.rotate_sign_in_token --db dev.db --email admin@lexgraph.local
  .venv/bin/python -m app.rotate_sign_in_token --db dev.db --user-id USER_ID
  ```

  Without `--db` it uses `LEXGRAPH_DATABASE_URL`. It refuses a database file
  that does not exist and creates nothing there, so a mistyped path cannot
  leave an empty `dev.db` behind. `--email` ignores letter case.

### Upgrading: sign-in tokens replace user-id sign-in

Older LexGraph versions used each account's user id as its sign-in
credential. User ids are visible to every member of a matter (rosters,
authors, reviewers), so on those versions any member could sign in as any
other member, including an admin. The `users.sign_in_token_hash` column
fixes that. A database created before it needs the
`20261116_sign_in_tokens` migration, which `python -m app.migrate --db PATH`
applies with every other pending one (see "Upgrading an existing
database"). Until it has run, the server refuses to start on the database
and names that command, because nobody could sign in.

To avoid locking anyone out, the migration gives every existing account a
**legacy** token equal to its old user id, so existing sign-ins (and saved
browser sessions) keep working. Those tokens are known to every member who
can see the ids, so **rotate them**:

1. Start the backend. It logs a warning naming the accounts that still
   sign in with their public user id.
2. List them at any time:
   `.venv/bin/python -m app.rotate_sign_in_token --db dev.db --list-legacy`.
3. Sign in as an admin (with your old user id), open Admin → **User
   accounts**, where those accounts carry a **Legacy sign-in** badge, and
   **Rotate token** for each, starting with your own; hand each new token
   to its owner. Accounts on matters you do not administer must be rotated
   by their matter's admin or with the command-line tool.

Rotated accounts sign in with their new token only; their old user id no
longer works.

### Upgrading: case-insensitive emails

Older versions stored email addresses as typed and compared them exactly,
so `Dana@Firm.example` and `dana@firm.example` could become two accounts
(and two simultaneous creations could even store one address twice).
Addresses are now stored in lowercase and must be unique, enforced by the
unique index `ix_users_email`. On an existing database, `python -m
app.migrate` applies this with the other migrations
(`20261116_users_email_unique`): it lowercases the stored addresses and adds
the index.

If two or more accounts already share an address in any letter case, it
changes none of them and leaves the index out. The run still exits 0: its
line for this migration reads `waiting for an operator`, and it ends by
naming each such account's user id and stored address. Until you resolve
them the app keeps working, but refuses to guess: the server starts and logs
the same list as a warning, and creating an account with that address, or
adding it to a matter, is refused (409). Decide which account keeps the
address, give each other account its own, and run the migration again
(nothing is deleted or merged). With `LEXGRAPH_DATABASE_URL` exported as in
"Initialize the Database", replace `USER_ID` and the new address:

```bash
cd backend
.venv/bin/python -c "
from sqlalchemy import text
from app.config import get_settings
from app.db import make_engine

with make_engine(get_settings().database_url).begin() as conn:
    conn.execute(text('UPDATE users SET email = :email WHERE id = :id'),
                 {'email': 'dana.old@firm.example', 'id': 'USER_ID'})
"
.venv/bin/python -m app.migrate
cd ..
```

The last command creates the index once no address is shared any more and
ends with `the schema is current`.

### Serving the web app in production

The production deployment is a single process. Build the web app once, and the backend serves it on its own port, on the same origin as the API:

```bash
npm --prefix frontend ci            # first time only
npm --prefix frontend run build     # writes frontend/dist/
cd backend
LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000
```

Open `http://localhost:8000` and sign in. At startup the backend logs `Serving the web app from .../frontend/dist`. Without a build it serves the API only (`GET /` is a 404). It looks for the build once, at startup, so build first. It listens on `127.0.0.1` only; to serve other computers, keep it that way and follow "Keep the backend on this machine" under "Starting the Backend".

- `/` and any other page path return the app's `index.html`, sent with `Cache-Control: no-cache` so browsers revalidate it on every load. The app routes with URL hashes (`/#/knowledge`), so deep links and reloads need nothing more.
- `/assets/*` serves the build's content-hashed files, which browsers may cache for a year.
- `/api/v1/*`, `/docs`, `/redoc`, `/openapi.json` and `/healthz` answer exactly as without the web app. An unknown `/api/...` path is still a JSON 404, and a wrong method is still a 405.
- `LEXGRAPH_FRONTEND_DIST=/path/to/dist` serves a build from another directory, for example when the backend is installed as a package. Set it to an empty value to serve the API only. If the directory has no `index.html`, the backend exits at startup with the command to build it.
- The build uses Vite 8's default browser target, `baseline-widely-available`: Chrome and Edge 111+, Firefox 114+, Safari 16.4+ (iOS 16.4+).

To check a build without the backend serving it, run `npm --prefix frontend run preview`. Vite's preview server serves `frontend/dist`, proxies `/api` to `http://127.0.0.1:8000` (or `LEXGRAPH_API_PROXY`) like the dev server, and prints the URL to open. It is a local check, not a production server.

The app calls `/api/v1` on its own origin and the backend sends no CORS headers, so these do **not** work:

- a static file host that does not forward `/api/` to the backend: sign-in fails with "Could not reach the LexGraph server" (the host's own 404 or 405 for `/api/v1/me`; only the backend's 401 reads "Unknown sign-in token");
- a build whose `VITE_API_BASE` points at another origin: the browser blocks every call ("Could not reach the LexGraph server");
- opening `frontend/dist/index.html` from disk (`file://`): a blank page.

Anything else in front of the app (a reverse proxy, a CDN) must serve `frontend/dist` and forward `/api/` to the backend on the same origin.

## MCP Server Registration

### Standalone MCP Server

The LexGraph MCP server exposes local assertion discovery and, when an agent account is configured, validated suggestion tools. See [MCP registration](mcp-registration.md). To run the MCP server standalone:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
cd backend
.venv/bin/python -m app.mcp.server
```

The MCP server reads from the `LEXGRAPH_DATABASE_URL` environment variable and communicates via stdio.
It checks the database before serving. If the URL is unset or in-memory, names a
file that does not exist, names a file without the LexGraph schema or one an
older LexGraph created (the line then names the `python -m app.migrate` command),
or `LEXGRAPH_AGENT_USER_ID` names no user, it prints one line starting
`lexgraph MCP server:` on stderr and exits non-zero. It never creates or changes
a database file.

### Integration with AI Agents

To use the LexGraph MCP with Claude Code, Codex, Cursor, or Antigravity, see the registration instructions in `docs/mcp-registration.md`.

For Claude Code, run this from the repository root. It registers absolute paths
because clients start the server from their own working directory, and they
do not inherit an `export`:

```bash
claude mcp add lexgraph \
  --env LEXGRAPH_DATABASE_URL="sqlite:///$(pwd)/backend/dev.db" \
  -- "$(pwd)/backend/.venv/bin/python" -m app.mcp.server
```

This targets the `backend/dev.db` that the Quickstart and step 2 of the
[end-to-end workflow](#end-to-end-workflow) create; adjust the file name for
another database. Add `--env LEXGRAPH_AGENT_USER_ID=<agent account id>` before
`--` to enable `agent_context` and `suggest_assertion`. Without it, the
suggestion tools are not registered.

## Running Tests

### Backend Tests

Run the backend test suite:

```bash
backend/.venv/bin/pytest backend/tests -v
```

To run only specific tests:

```bash
backend/.venv/bin/pytest backend/tests/unit/test_enrichment_suggester.py -v
```

To run only the definition-linking tests:

```bash
backend/.venv/bin/pytest backend/tests/unit/test_definition_links_*.py backend/tests/integration/test_definition_links_*.py -v
```

### Frontend Tests

Run the frontend test suite:

```bash
npm --prefix frontend run test -- --run
```

## End-to-End Workflow

Here's a complete workflow from fresh clone to a working, admin-provisioned
local-first LexGraph system — bootstrap → sign in → create users → grant
access, per the "Quickstart" and "Provisioning users & access" sections
above:

1. **Clone and setup**:
   ```bash
   git clone https://github.com/vicciz-ceo/LexGraph.git
   cd LexGraph
   (cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')
   npm --prefix frontend ci
   ```

2. **Bootstrap the workspace** (one-time; creates the schema, the first
   organization/matter, and the first admin — see "Quickstart" above):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
   cd backend
   .venv/bin/python -m app.bootstrap
   cd ..
   ```
   Copy the printed sign-in token — it's the admin's credential and is
   shown only once.

3. **Start the backend** (Terminal 1):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///$PWD/backend/dev.db"
   cd backend
   .venv/bin/uvicorn app.main:app --port 8000
   ```

4. **Start the web app** (Terminal 2):
   ```bash
   npm --prefix frontend run dev
   ```
   For a deployment, skip this terminal instead: run
   `npm --prefix frontend run build` once, then start (or restart) the backend
   from step 3, which serves the app at `http://localhost:8000` (see "Serving
   the web app in production"; the backend looks for the build only at startup).

5. **Access the application**:
   - Grading app: `http://localhost:5173` — sign in with the token from step 2
   - Backend API docs: `http://localhost:8000/docs`

6. **Create users and grant access** — from the signed-in admin session:
   Admin → User accounts → create an account (copy its sign-in token, shown
   once) → Admin → Members & roles → grant it a role on a matter. See
   "Provisioning users & access" above for the full walkthrough.

7. **Optional: Register MCP server** (Terminal 3, from the repository root;
   uses the `backend/dev.db` created in step 2):
   ```bash
   claude mcp add lexgraph \
     --env LEXGRAPH_DATABASE_URL="sqlite:///$(pwd)/backend/dev.db" \
     -- "$(pwd)/backend/.venv/bin/python" -m app.mcp.server
   ```
   To let an agent suggest assertions, also pass
   `--env LEXGRAPH_AGENT_USER_ID=<id>` (before `--`) with a dedicated agent
   account from step 6 that has contributor membership. See
   [mcp-registration.md](mcp-registration.md) for Codex and other clients.

## Environment Variables

- `LEXGRAPH_DATABASE_URL`: SQLite database URL, best given in the absolute four-slash form (`sqlite:////abs/path/backend/dev.db`, or `"sqlite:///$PWD/backend/dev.db"` from the repository root; a relative `sqlite:///dev.db` resolves against the current directory). Defaults to in-memory if not set, which the server, the agent CLI and the MCP server refuse. `python -m app.bootstrap`, `app.migrate` and `app.rotate_sign_in_token` accept `--db PATH` instead. `app.seed_demo` does not read it: it writes the file given by `--db` (default `dev.db` in the current directory).
- `LEXGRAPH_AGENT_USER_ID`: the dedicated agent account used by the agent CLI and the MCP server (see [AGENT_GUIDE.md](AGENT_GUIDE.md)). Unset, the MCP server is read-only.
- `LEXGRAPH_FRONTEND_DIST`: the web app build the backend serves on its own origin (default: `frontend/dist` when it has been built; empty value: API only). See "Serving the web app in production".
- `LEXGRAPH_API_PROXY`: where the Vite dev and preview servers forward `/api` (default `http://127.0.0.1:8000`).
- `VITE_API_BASE` (build time): the API base path the web app calls (default `/api/v1`). It must stay on the app's own origin, because the backend sends no CORS headers.

## Troubleshooting

- **Database connection errors**: Ensure `LEXGRAPH_DATABASE_URL` is set correctly and the file path is writable.
- **A request answers 503 "The database is busy" (`database is locked`)**: another process kept the SQLite database locked for longer than the server waits for it (5 seconds), for example many agent submissions at once, a long pipeline batch, or a `sqlite3` shell left inside a transaction. Nothing is left half-written: a write that could not finish is rolled back, so repeat the request a moment later (the response's `Retry-After` header gives the seconds; in the web app, which shows the message, try the action again). The server logs a warning with the request's `X-Request-ID` for each one; if they keep coming, find the process that holds the database open in a transaction. The agent CLI and MCP server report the same condition as status 500 with `database is locked` in the error.
- **`LexGraph cannot start: ...` / `Application startup failed`**: the server checked the database and printed the fix. Run the `python -m app.bootstrap` or `python -m app.migrate` command it names (see "Upgrading an existing database"), then start it again.
- **Sign-in says "Could not reach the LexGraph server" although the backend is running**: the page is not being served by the backend (or by a proxy that forwards `/api/` to it). See "Serving the web app in production". "Unknown sign-in token" is the backend itself refusing the token: check it, or have it rotated. With the dev or preview server, first check that it forwards to your backend (see "Port already in use" below): another backend on port 8000 refuses your token too.
- **An agent CLI or MCP error says the database was created by an older version of LexGraph**: run the `python -m app.migrate --db PATH` command it names. Both run the server's schema check before they touch the database.
- **The server logs `The database lacks the unique index ix_users_email until an operator acts`**: accounts share an email address; see "Upgrading: case-insensitive emails".
- **Port already in use**: Start the backend on another port with `--port 8001`. The web app's dev and preview servers still forward `/api` to `http://127.0.0.1:8000`, whatever holds that port (often another LexGraph checkout, with its own database), so point them at the moved backend: `LEXGRAPH_API_PROXY=http://127.0.0.1:8001 npm --prefix frontend run dev` (the same for `run preview`). To move the web app itself, use `npm --prefix frontend run dev -- --port 5174 --strictPort` (without `--strictPort`, Vite picks the next free port on its own). For `./scripts/demo.sh`, set `BACKEND_PORT` or `FRONTEND_PORT` (see "Optional: demo workspace"); its proxy follows the backend port.
- **Module not found errors**: Ensure you've installed the backend with `(cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')` from the repository root, and that you start LexGraph with `backend/.venv/bin/...`, not a system `python3`.
- **MCP server shows "Failed to connect"**: run the registered command by hand
  with the same environment, e.g.
  `LEXGRAPH_DATABASE_URL=sqlite:////abs/path/backend/dev.db /abs/path/backend/.venv/bin/python -m app.mcp.server < /dev/null`.
  It prints the reason on one stderr line (a working configuration prints
  nothing and exits when stdin closes). A relative `sqlite:///` URL
  resolves against the client's working directory, not `backend/`, so register
  the absolute four-slash URL as shown in step 7.

## Agent suggestions and lawyer collaboration

See [AGENT_GUIDE.md](AGENT_GUIDE.md) for the validated local JSON CLI, REST
submission contract, provenance and lawyer workflow, and
[mcp-registration.md](mcp-registration.md) for Claude Code/Codex configuration.
Use the same absolute database URL for backend, CLI and MCP. A database from an
older LexGraph release needs `python -m app.migrate` first (see "Upgrading an
existing database"); on a current database it changes nothing. Agent writes are
opt-in through a dedicated contributor account; existing no-actor MCP clients
retain their original whole-database read-only mode.
