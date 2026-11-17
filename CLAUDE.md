# LexGraph

Read @AGENTS.md for repository and assertion-authoring instructions, and
@docs/AGENT_GUIDE.md for the local database submission workflow.

When the LexGraph MCP server is configured, start with `assertion_guide`, then
`agent_context`. Use `suggest_assertion` for proposals with evidence and
platform/model provenance. If the client reports the server as failed, run its
registered command by hand to read the one-line reason
([MCP registration](docs/mcp-registration.md)). Without MCP, use the JSON CLI,
`backend/.venv/bin/python -m app.agent_cli` from the repository root, as
explained in the guide. No hosted model API or web server is required by the CLI.
