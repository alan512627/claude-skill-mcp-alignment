---
name: feedback-bash-mount-sync-lag
description: "The Linux sandbox's bash mount of connected folders can lag behind what Read/Write/Edit just wrote — never use bash cp to deploy a just-edited file, verify via Read"
type: feedback
project: Local-C9A17
---

The bash tool's view of a connected folder (via its `/sessions/.../mnt/...` FUSE mount) can be stale relative to what the Write/Edit tools just wrote to the real Windows path. After editing a file with Edit/Write, immediately running `wc -l` or `cat` on it through the bash mount returned old content even seconds later, while Read on the Windows path showed the correct content.

**Why:** This caused at least two rounds of shipping broken HTML reports in the C9A17 folder-report workflow — `cp`-ing from the outputs mount to the C9A17 mount picked up a stale, half-edited snapshot (tabs/content silently missing).

**How to apply:** When deploying a just-edited file, write directly to the final Windows path with Write rather than editing in outputs and `cp`-ing via bash. If bash `cp` must be used, verify with Read on the actual Windows path, not a bash read-back. Related: [[feedback_html_tab_switching_compat]].
