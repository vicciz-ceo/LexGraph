# LexGraph Local-First Install Runbook

This runbook describes how to set up and run a complete local-first LexGraph system from a fresh clone, with zero cloud dependencies. The system consists of:
1. A local SQLite database
2. A FastAPI backend server
3. A React grading application
4. An MCP server for agent integration

## Fresh-Clone Setup

Start with a clean clone of the repository:

```bash
git clone https://github.com/vicciz-ceo/LexGraph.git
cd LexGraph
```

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

## Grading Application

### Starting the Grading App

In a separate terminal, start the Vite development server for the frontend grading application:

```bash
npm --prefix frontend run dev
```

The grading application will be available at `http://localhost:5173` (or the port specified by Vite). This application allows you to:
- View all assertions and evidence
- Create new assertions
- Rate and review suggested assertions
- Edit existing assertions and comments

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

Here's a complete workflow from fresh clone to a working local-first LexGraph system:

1. **Clone and setup**:
   ```bash
   git clone https://github.com/vicciz-ceo/LexGraph.git
   cd LexGraph
   cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e '.[dev]' && cd ..
   npm --prefix frontend ci
   ```

2. **Initialize database** (one-time schema creation — see "Database Schema" above):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
   cd backend
   .venv/bin/python -c "import app.models; from app.config import get_settings; from app.db import Base, make_engine; Base.metadata.create_all(make_engine(get_settings().database_url))"
   cd ..
   ```

3. **Start the backend** (Terminal 1):
   ```bash
   export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
   cd backend
   .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Start the grading app** (Terminal 2):
   ```bash
   npm --prefix frontend run dev
   ```

5. **Access the application**:
   - Grading app: `http://localhost:5173`
   - Backend API docs: `http://localhost:8000/docs`

6. **Optional: Register MCP server** (Terminal 3):
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
