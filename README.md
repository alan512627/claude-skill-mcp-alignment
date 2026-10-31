# claude-skill-mcp-alignment
## Skills

- [ntttcp-full-duplex-throughput-analysis](ntttcp-full-duplex-throughput-analysis/SKILL.md) — evidence-based analysis of NTTTCP full-duplex bare-metal log bundles with HTML dashboard and raw-log excerpts.

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
