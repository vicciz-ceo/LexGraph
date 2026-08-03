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

### Quickstart (real provisioning)

The real path from an empty database to a working, admin-owned instance:
bootstrap the workspace, sign in as the admin bootstrap creates, then
provision further users and access from the app itself.

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m app.bootstrap --db dev.db
```

Bootstrap refuses to run on a non-empty database (an empty-DB guard — no
silent mutation on top of an existing workspace) and prints the new admin's
sign-in id — that id **is** the credential (`backend/app/auth.py`'s
test-token seam: `Authorization: Bearer <user_id>`); there are no passwords.
Copy it, then start both servers:

```bash
LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000
cd .. && npm --prefix frontend install && npm --prefix frontend run dev
```

Sign in at http://localhost:5173 with the printed id. From there, use
Admin → User accounts to create further accounts and Admin → Members &
roles to grant them roles on a matter — see
["Provisioning users & access"](#provisioning-users--access) below for the
full flow. The rest of this runbook is the manual, step-by-step breakdown
of what bootstrap and the demo seed each automate.

### Optional: demo workspace (local testing / mockup data)

`./scripts/demo.sh` is a local-testing convenience, not a provisioning
path — it seeds a demo workspace into `backend/dev.db` with fixed,
hardcoded accounts and starts backend (:8000) + frontend (:5173) in one
command:

```bash
./scripts/demo.sh
```

Sign in at http://localhost:5173 as `admin`, `reviewer`, `contributor`, or
`viewer` (the user id *is* the role name — no admin action created these;
they're fixtures for exercising the UI locally). The seeder
(`backend/app/seed_demo.py`) drives the real API, so the demo data carries
genuine revisions, ratings, comments, notifications, and audit events —
useful for development and mockups, not for a real deployment.

### Backend Environment Setup

Initialize the backend virtual environment and install dependencies:

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cd ..
```

### Frontend Environment Setup

Install frontend dependencies:

```bash
npm --prefix frontend ci
```

## Database Setup

### Initialize the Database

LexGraph uses SQLite as the default local database. Create a new database file or use an in-memory database by setting the environment variable:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
```

For an in-memory database (no persistence), omit this variable:

```bash
unset LEXGRAPH_DATABASE_URL
```

### Database Schema

The backend does **not** create the schema automatically — `create_app()` never calls `Base.metadata.create_all()` (only the test fixtures do). Against a fresh database, uvicorn starts and `/healthz` passes, but every real API call fails with `no such table` errors.

Before starting the backend against a new file-backed database, create the schema manually (one-time step):

```bash
cd backend
LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db" .venv/bin/python -c "
import app.models  # register ORM mappings
from app.config import get_settings
from app.db import Base, make_engine

Base.metadata.create_all(make_engine(get_settings().database_url))
"
cd ..
```

Note: this step only applies to file-backed databases. With the in-memory default (`LEXGRAPH_DATABASE_URL` unset), a separate process cannot populate the server's database — use a file-backed URL for any real usage.

### Migration: Adding Raw-Text Columns

If you are upgrading from a version of LexGraph before the raw-text columns were added (raw columns for proposition, comment, and rationale), you must run the migration to add these columns:

```bash
cd backend
python3.13 -c "
from app.migrations.add_raw_text_columns import upgrade
from app.db import make_engine
from app.config import get_settings

settings = get_settings()
engine = make_engine(settings.database_url)
upgrade(engine)
"
cd ..
```

### Backfill: Historical Rows

The migration adds three new columns:
- `proposition_raw` in `assertion_revisions`
- `comment_text_raw` in `assertion_comments`
- `rationale_raw` in `assertion_ratings`

For any existing database with rows created before this upgrade, the migration automatically backfills these raw columns from their sanitized counterparts. This means historical rows will contain the sanitized approximation of the text, not the original bytes, because the original raw text is no longer available at the time of migration. New rows created after the migration will store both the original raw text and the sanitized version.

If you need to downgrade and remove these columns, run:

```bash
cd backend
python3.13 -c "
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
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
cd backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`. Check the health status with:

```bash
curl http://localhost:8000/healthz
```

### Backend REST API

The backend provides REST APIs at `/api/v1/` for managing assertions, comments, ratings, and the graph. See the API documentation at `http://localhost:8000/docs` when the server is running.

### Offline Pipelines (CLI-only, no frontend UI)

Two deterministic, offline batch passes run against a matter's already-stored data and write draft/accepted assertions directly to the database (no LLM/network calls). Both read `LEXGRAPH_DATABASE_URL` the same way the backend server does, so point them at the same database file the server uses.

**Enrichment** (`app/enrich/`) suggests candidate assertions from existing `SourceSpan` rows:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
cd backend
.venv/bin/python -m app.enrich.cli --matter-id <matter-id> --triggered-by-user-id <user-id>
cd ..
```

**Definition linking** (`app/definition_links/`, sprint 2026-07-29-definition-links) deterministically (regex/rule-based, no LLM/ML) connects articles within a law to the definitions the law contains, and connects laws to each other when a definition explicitly derives from another law (e.g. "כהגדרתו בחוק..."). It requires `Article` rows already ingested via `app.definition_links.ingest.ingest_wiki_law` (there is no ingestion CLI yet — call `ingest_wiki_law(session, ...)` directly, e.g. from a one-off script or a REPL, to load a `.wiki`-formatted law's text into `Document`/`Article`/`SourceSpan` rows for a matter):

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
cd backend
.venv/bin/python -m app.definition_links.cli --matter-id <matter-id> --triggered-by-user-id <user-id>
cd ..
```

This writes `USES_DEFINITION` (an article uses a term defined elsewhere in the same law) and `DERIVES_FROM_LAW` (a definition explicitly derives from another law) assertions with `origin=system_generated`, `status=accepted`. An unresolved cross-law derivation (the target law was never ingested into this matter) is still recorded, with a null object entity and the raw matched law-reference text preserved in the proposition — never dropped, never a fabricated resolution. An article whose text shows reversed-word-order (bidi-degraded) artifacts is flagged and skipped, never auto-corrected. The pass is idempotent — rerunning it over unchanged articles creates no additional rows. Results are visible via the existing `GET /api/v1/assertions?matter_id=<id>&origin=system_generated` endpoint (no dedicated route or frontend UI this sprint).

### Ingesting US statutes (`vaquill/open-us-law` dataset)

Sprint 2026-08-02-us-state-law (item 5, gate G6) adds an ingester for the
[`vaquill/open-us-law`](https://huggingface.co/datasets/vaquill/open-us-law)
Hugging Face dataset (109 Parquet files, ~1.1GB, ~2M sections — 50 states +
DC + PR + federal, statutes + constitutions). `pyarrow` is a real backend
dependency (see `backend/pyproject.toml`) so `pip install -e '.[dev]'` in
the "Backend Environment Setup" step above already installs it.

Each Parquet file is ingested with **one command**, which creates one
`Document` (using `--title`) and one `Article` + `SourceSpan` per row:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
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

**Ingesting the full 109-file corpus (gate G6) is ONE command** using
`--input-dir` instead of `--input` — bulk directory mode, not a shell loop
around the single-file command. Point it at the directory holding all 109
downloaded Parquet files:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
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
it never aborts the whole 109-file run over one bad file. A final summary
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

The `.venv/bin/python` process itself never downloads the dataset — fetch
the 109 Parquet files first (e.g. via `huggingface_hub.hf_hub_download` or
the Hugging Face CLI) into one local directory and point `--input-dir` (or
`--input` for a single file) at it.

## Web Application

### Starting the Web App

In a separate terminal, start the Vite development server:

```bash
npm --prefix frontend run dev
```

The app will be available at `http://localhost:5173` (or the port specified by Vite); the dev server proxies `/api` to `http://127.0.0.1:8000` (override with `LEXGRAPH_API_PROXY`). Sign in with a user id that exists in the connected database — the bearer token *is* the user id (`backend/app/auth.py` test-token seam); with the demo seed that means `admin`, `reviewer`, `contributor`, or `viewer`.

The UI implements the Consensus design system (see [docs/design/consensus-ui-review.md](design/consensus-ui-review.md)):
- **Review Queue** — proposed assertions with strength-rating summaries; reviewers accept/reject/dispute/request revisions
- **Knowledge Base** — searchable accepted-assertion table with CSV export
- **Suggest Assertion** — contributor submission flow with evidence spans and duplicate warnings
- **Assertion detail** — evidence, comments, revision history, ratings, and role-gated review actions
- **Contested** — adjudication queue for disputed assertions
- **Analytics** — per-matter dashboard computed live from the assertion list
- **Admin** — user account provisioning and matter member/role management (admin role required)
- **Profile** — your activity, notifications, and matters

### Provisioning users & access

Once signed in as an admin (bootstrap prints the first one — see
["Quickstart"](#quickstart-real-provisioning) above), provisioning further
people is entirely in-app; no CLI or DB access is required:

1. **Create the account.** Admin → **User accounts** → fill in email and
   display name → **Create account**. The response — and the page — show
   the new account's sign-in id prominently. That id **is** the sign-in
   credential (there are no passwords); hand it to the person. Creating an
   account pre-fills its email into the Members & roles add-member field
   so granting access is the very next step.
2. **Grant matter access.** Admin → **Members & roles** → the new
   account's email is already filled in → pick a role (viewer,
   contributor, reviewer, or admin) → **Add**. Roles are per-matter: the
   same account can be a reviewer on one matter and have no access to
   another, and admin is a per-matter admin, not a global superuser role
   (any admin-of-some-matter can list/create user accounts, per the users
   API's access model).
3. **They sign in.** The new user enters the id from step 1 on the
   sign-in page and immediately sees the UI appropriate to the role(s)
   they were granted.

This replaces hand-editing the database or re-running the demo seed for
real usage — the seed stays a local-testing convenience (see "Optional:
demo workspace" above), never the provisioning path for an actual
deployment.

### Building for Production

To build the frontend for production:

```bash
npm --prefix frontend run build
```

## MCP Server Registration

### Standalone MCP Server

The LexGraph MCP server exposes the local database as read-only tools for AI agents. To run the MCP server standalone:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
cd backend
.venv/bin/python -m app.mcp.server
```

The MCP server reads from the `LEXGRAPH_DATABASE_URL` environment variable and communicates via stdio.

### Integration with AI Agents

To use the LexGraph MCP with Claude Code, Codex, Cursor, or Antigravity, see the registration instructions in `docs/mcp-registration.md`.

For Claude Code, the basic command is:

```bash
claude mcp add lexgraph -- backend/.venv/bin/python -m app.mcp.server
```

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
   cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e '.[dev]' && cd ..
   npm --prefix frontend ci
   ```

2. **Bootstrap the workspace** (one-time; creates the schema, the first
   organization/matter, and the first admin — see "Quickstart" above):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
   cd backend
   .venv/bin/python -m app.bootstrap
   cd ..
   ```
   Copy the printed sign-in id — it's the admin's credential.

3. **Start the backend** (Terminal 1):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
   cd backend
   .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Start the web app** (Terminal 2):
   ```bash
   npm --prefix frontend run dev
   ```

5. **Access the application**:
   - Grading app: `http://localhost:5173` — sign in with the id from step 2
   - Backend API docs: `http://localhost:8000/docs`

6. **Create users and grant access** — from the signed-in admin session:
   Admin → User accounts → create an account (copy the returned sign-in
   id) → Admin → Members & roles → grant it a role on a matter. See
   "Provisioning users & access" above for the full walkthrough.

7. **Optional: Register MCP server** (Terminal 3):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
   claude mcp add lexgraph -- backend/.venv/bin/python -m app.mcp.server
   ```

## Environment Variables

- `LEXGRAPH_DATABASE_URL`: SQLite database URL (e.g., `sqlite:///lexgraph.db`). Defaults to in-memory if not set.

## Troubleshooting

- **Database connection errors**: Ensure `LEXGRAPH_DATABASE_URL` is set correctly and the file path is writable.
- **Port already in use**: Change the port with `--port 8001` for the backend or Vite configuration for the frontend.
- **Module not found errors**: Ensure you've run `pip install -e '.[dev]'` in the backend directory.
