# claude-skill-mcp-alignment
## Skills

- [ntttcp-full-duplex-throughput-analysis](ntttcp-full-duplex-throughput-analysis/SKILL.md) — evidence-based analysis of NTTTCP full-duplex bare-metal log bundles with HTML dashboard and raw-log excerpts.
- [fw-recipe-comparator](fw-recipe-comparator/SKILL.md) — single-file HTML firmware recipe comparison tool (Excel import, LCS diff, severity, timeline, PDF/Excel export).
- [fastfm](fastfm/SKILL.md) — working rules for the FastFM project (Tauri 2 Windows file manager, Rust + vanilla JS).
- [compilerless-verification](compilerless-verification/SKILL.md) — shipping correct changes when you cannot compile/run: static gates, assert-guarded edits, behaviour regression checks.
- [clude-follow-up-rule](clude-follow-up-rule/SKILL.md) — strict working rules to keep Claude's error rate low.

## Sync on any machine (one command)

Claude's built-in memory is stored per machine, so this repo is the shared source: `memory/` (shared memory), one folder per skill, and `claude-block.md` (rules injected into `~/.claude/CLAUDE.md`).

Windows (PowerShell):

```
irm https://raw.githubusercontent.com/alan512627/claude-skill-mcp-alignment/main/setup.ps1 | iex
```

macOS / Linux / Git-Bash:

```
bash <(curl -fsSL https://raw.githubusercontent.com/alan512627/claude-skill-mcp-alignment/main/setup.sh)
```

The script clones or pulls the repo to `~/claude-skill-mcp-alignment`, writes a managed block into `~/.claude/CLAUDE.md` (between `claude-sync` markers, replaced on every run), and copies every skill folder to `~/.claude/skills/`. Re-run it any time to sync; restart Claude Code afterwards.

**Privacy:** if this repo is public, everything in `memory/` is public. Keep it private if memories may contain personal info, and never store secrets.

## Other synced content

- `memory/claude-ai/` — claude.ai account memory (profile, areas, topics, per-Project memory for Callan, Local-C9A17, C4143 scale log analysis). Passwords/credentials and internal share hosts are redacted.
- `conversations/` — index + summary of every claude.ai chat (outside Projects). Summaries only; full transcripts come from claude.ai → Settings → Privacy → Export data.
- `mcp/servers.md` — plugin/MCP inventory per machine plus claude.ai account connectors.

