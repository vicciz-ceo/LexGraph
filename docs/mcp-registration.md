# LexGraph MCP Registration

The LexGraph backend includes a local MCP (Model Context Protocol) server that exposes the graph database as read-only tools for AI agents. This server reads the local SQLite database and provides no network access — the MCP exposes the entire local database read-only, with no per-matter permission filtering. It is the session's map of the user's own local data.

The MCP server runs as a stdio process and provides three tools:
- **explore**: Query assertions and evidence with relationships in a single bounded call
- **search**: Full-text search across the database
- **fetch**: Retrieve specific records by ID

## Claude Code Registration

To register the LexGraph MCP with Claude Code, use the following command:

```bash
claude mcp add lexgraph -- backend/.venv/bin/python -m app.mcp.server
```

Ensure the `LEXGRAPH_DATABASE_URL` environment variable is set before running Claude Code. For example:

```bash
export LEXGRAPH_DATABASE_URL="sqlite:///lexgraph.db"
```

## Codex Configuration

For Codex, add the following to your MCP configuration file (typically `~/.codex/mcp.json` or similar):

```json
{
  "mcpServers": {
    "lexgraph": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/path/to/lexgraph/backend",
      "env": {
        "LEXGRAPH_DATABASE_URL": "sqlite:///lexgraph.db"
      }
    }
  }
}
```

## Cursor Configuration

For Cursor, configure the MCP server in your Cursor settings or configuration file:

```json
{
  "mcp": {
    "servers": {
      "lexgraph": {
        "command": "python",
        "args": ["-m", "app.mcp.server"],
        "cwd": "/path/to/lexgraph/backend",
        "env": {
          "LEXGRAPH_DATABASE_URL": "sqlite:///lexgraph.db"
        }
      }
    }
  }
}
```

## Antigravity Configuration

For Antigravity, configure the LexGraph MCP server using the following configuration:

```json
{
  "mcpServers": {
    "lexgraph": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/path/to/lexgraph/backend",
      "env": {
        "LEXGRAPH_DATABASE_URL": "sqlite:///lexgraph.db"
      }
    }
  }
}
```

## Running the MCP Server Standalone

To test the MCP server outside of any client, run:

```bash
python -m app.mcp.server
```

The server reads the database URL from the `LEXGRAPH_DATABASE_URL` environment variable. If not set, it defaults to an in-memory SQLite database.

## Database

The MCP server is read-only and connects to the same SQLite database as the grading app. Set `LEXGRAPH_DATABASE_URL` to point to your database file. Multiple clients can connect to the same MCP server instance, all reading from the same local database.
