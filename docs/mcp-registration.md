# LexGraph MCP registration

The local stdio server connects directly to LexGraph's database. Install the
backend first (`pip install -e '.[dev]'`). Use absolute paths so the Python module
and database resolve regardless of the agent's working directory.

Available tools:

- `assertion_guide`: workflow and complete submission JSON schema.
- `explore`, `search`, `fetch`: existing assertion lookup and evidence.
- `agent_context`: discover authorized matters, persisted entities, source spans
  and existing assertions (requires configured agent user).
- `suggest_assertion`: atomically create a model-suggested draft/proposal with
  evidence and provenance (requires configured agent user).

When `LEXGRAPH_AGENT_USER_ID` is configured, all reads and writes are restricted
to that user's matter memberships; suggestions require contributor access.
Without it the server retains its original **whole-local-database read-only**
mode, plus `assertion_guide`. Only use this mode with trusted local clients.

First create an agent account through Admin and grant contributor membership.
Replace all paths and `AGENT_USER_ID` below. These examples configure clients;
they do not start an LLM or make any provider API calls.

The server checks its configuration at startup. If `LEXGRAPH_DATABASE_URL` is
unset or in-memory, names a missing file or a file without the LexGraph schema,
or `LEXGRAPH_AGENT_USER_ID` names no user, it exits with one line on stderr
starting `lexgraph MCP server:` and creates no file, so the client reports the
server as failed. To read the reason, run the configured command by hand with
the same environment.

## Claude Code

```bash
claude mcp add lexgraph \
  --env LEXGRAPH_DATABASE_URL=sqlite:////absolute/path/to/LexGraph/backend/dev.db \
  --env LEXGRAPH_AGENT_USER_ID=AGENT_USER_ID \
  -- /absolute/path/to/LexGraph/backend/.venv/bin/python -m app.mcp.server
```

## Codex

```bash
codex mcp add lexgraph \
  --env LEXGRAPH_DATABASE_URL=sqlite:////absolute/path/to/LexGraph/backend/dev.db \
  --env LEXGRAPH_AGENT_USER_ID=AGENT_USER_ID \
  -- /absolute/path/to/LexGraph/backend/.venv/bin/python -m app.mcp.server
```

Alternatively use `~/.codex/config.toml`:

```toml
[mcp_servers.lexgraph]
command = "/absolute/path/to/LexGraph/backend/.venv/bin/python"
args = ["-m", "app.mcp.server"]

[mcp_servers.lexgraph.env]
LEXGRAPH_DATABASE_URL = "sqlite:////absolute/path/to/LexGraph/backend/dev.db"
LEXGRAPH_AGENT_USER_ID = "AGENT_USER_ID"
```

Codex supports stdio MCP registration through its CLI or TOML configuration;
see the [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
Command syntax was also checked against the locally installed clients' help.

## Cursor, Antigravity and other clients

Use the client's stdio MCP configuration with the same command, arguments and
environment. For clients that accept `mcpServers` JSON:

```json
{
  "mcpServers": {
    "lexgraph": {
      "command": "/absolute/path/to/LexGraph/backend/.venv/bin/python",
      "args": ["-m", "app.mcp.server"],
      "env": {
        "LEXGRAPH_DATABASE_URL": "sqlite:////absolute/path/to/LexGraph/backend/dev.db",
        "LEXGRAPH_AGENT_USER_ID": "AGENT_USER_ID"
      }
    }
  }
}
```

Clients differ in config location and wrapper keys; use their stdio settings.
Agents without MCP can use the JSON CLI or HTTP API in the
[agent guide](AGENT_GUIDE.md). No web server is needed for CLI or MCP.

After connecting, ask the agent to call `assertion_guide`, then `agent_context`,
read the relevant sources, and call `suggest_assertion` with `payload` set to a
schema-valid JSON object. Proposed assertions appear in the lawyers' review queue.

A failed call returns an error result whose text is `Error executing tool <name>: `
followed by the JSON object the CLI prints, for example
`{"error": "duplicate: an identical proposition already exists in this matter (assertion <id>)", "status": 409}`.
Schema violations add `issues` (`field` and `message` for each). The statuses
mean the same as in the [agent guide](AGENT_GUIDE.md#persistence-and-errors).
