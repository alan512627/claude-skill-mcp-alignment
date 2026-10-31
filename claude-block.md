## Personal Claude sync (managed by setup script — do not edit between the markers)

Shared memory and skills live in the git repo cloned at `~/claude-skill-mcp-alignment` (https://github.com/alan512627/claude-skill-mcp-alignment, branch main). The same repo is used on all my computers.

- At the start of a conversation run `git -C ~/claude-skill-mcp-alignment pull --ff-only` (skip silently if offline). If the pull brought new commits, immediately re-read `memory/MEMORY.md` and any changed memory files (the index below was loaded before the pull), then use them.
- Plugin/MCP inventory per machine is in `mcp/servers.md` (names only, no credentials). When asked to sync a machine, merge its memories, skills and plugin/MCP list into the repo and push.
- To remember something new: write it as one file in `~/claude-skill-mcp-alignment/memory/` (same frontmatter format as normal auto-memory), add one line to `memory/MEMORY.md`, then commit and push to main. Do NOT write to the machine-local memory folder. Never store passwords, tokens or other secrets in it.
- Skills: one folder per skill at the repo root (`<skill-name>/SKILL.md` + `scripts/`, `assets/`), listed in README.md. Save new skills there (commit + push). At the start of a task that might relate to past work, check the repo's README/SKILL.md descriptions for a relevant skill, use it and tell me which one.
- After adding or changing a skill, re-run the setup script so `~/.claude/skills/` is refreshed.

@~/claude-skill-mcp-alignment/memory/MEMORY.md
