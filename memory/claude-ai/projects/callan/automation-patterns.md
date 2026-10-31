---
name: automation-patterns
description: Conventions for driving RSCM/HRU consoles over SSH — prompt transitions, session entry/exit, logging, subprocess launching
project: Callan
---
- [stated] Every prompt transition must be confirmed before sending the next command (`RScmCli#` → RSCM, `HRU {admin}>` → HRU console, `bash-5.0#` → bash shell)
- [stated] HRU console entered via `start cdu serial session`; exited with `~.` (tilde-dot SSH escape, preceded by Enter to ensure line-start)
- [stated] All log output requires individual per-line timestamps
- [stated] Subprocess launching: use `subprocess.Popen` with a list argument and `creationflags=subprocess.CREATE_NEW_CONSOLE` (not `shell=True`) to avoid Windows path/quoting errors
