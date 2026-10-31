# Plugins / MCP inventory (names only — no tokens, no credentials)

Merge each machine's list into this file (add a `Machine:` section per computer, keep one line per item).
OAuth/login state is never stored here; on another machine re-authorize via `/mcp` or reinstall via `/plugin`.

## Machine: Windows desktop (user) — recorded 2026-10-31
Plugin marketplace: `claude-plugins-official` (github: anthropics/claude-plugins-official)
Locally installed plugins (from `~/.claude/plugins/data`): browser-use, carta-cap-table, carta-crm, carta-investors, cockroachdb, datadog, desktop-commander, gitkraken, pdf-viewer, prisma, render, research-desk, security-guidance, signalwire, superpowers
User-defined MCP servers in `~/.claude.json`: none
Note: connectors that appear as `mcp__<uuid>__*` (Gmail, Drive, Slack, Figma, Canva, Gamma, Adobe, etc.) belong to the claude.ai account and follow the account, not the machine.
