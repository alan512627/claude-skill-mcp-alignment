#!/usr/bin/env bash
# One-command sync for macOS/Linux/Git-Bash. Safe to re-run (it is also the "sync" command).
#   bash <(curl -fsSL https://raw.githubusercontent.com/alan512627/claude-skill-mcp-alignment/main/setup.sh)
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/alan512627/claude-skill-mcp-alignment.git}"
DIR="${CLAUDE_SYNC_DIR:-$HOME/claude-skill-mcp-alignment}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
BEGIN='<!-- claude-sync:begin -->'; END='<!-- claude-sync:end -->'

if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone "$REPO_URL" "$DIR"; fi
mkdir -p "$DIR/memory" "$CLAUDE_DIR/skills"
[ -f "$DIR/memory/MEMORY.md" ] || : > "$DIR/memory/MEMORY.md"

# managed block in ~/.claude/CLAUDE.md (replace between markers, else append)
F="$CLAUDE_DIR/CLAUDE.md"; touch "$F"
TMP="$(mktemp)"
awk -v b="$BEGIN" -v e="$END" '$0==b{skip=1} !skip{print} $0==e{skip=0}' "$F" > "$TMP"
{ cat "$TMP"; echo "$BEGIN"; cat "$DIR/claude-block.md"; echo "$END"; } > "$F"; rm -f "$TMP"

# install skills (every top-level folder with SKILL.md)
for d in "$DIR"/*/; do
  [ -f "$d/SKILL.md" ] || continue
  n="$(basename "$d")"; rm -rf "$CLAUDE_DIR/skills/$n"; cp -r "$d" "$CLAUDE_DIR/skills/$n"; echo "skill: $n"
done
echo "done. Restart Claude Code so CLAUDE.md and skills reload."
