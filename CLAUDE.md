# LexGraph

Read @AGENTS.md for repository and assertion-authoring instructions, and
@docs/AGENT_GUIDE.md for the local database submission workflow.

When the LexGraph MCP server is configured, start with `assertion_guide`, then
`agent_context`. Use `suggest_assertion` for proposals with evidence and
platform/model provenance. Without MCP, use `python -m app.agent_cli` as
explained in the guide. No hosted model API or web server is required by the CLI.
