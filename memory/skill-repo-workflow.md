---
name: skill-repo-workflow
description: "Rule - save every new skill to the user's skill repo, and search that repo for relevant skills at the start of each related task"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5a9efb91-4837-401f-9793-9b97c78963ad
  modified: 2026-10-31T03:23:41.488Z
---

1. **Saving**: whenever a skill is written from a conversation/work (user asks, or an analysis is turned into a skill), store it in the skill repo ([[skill-repo-location]]) as `<skill-name>/SKILL.md` (+ scripts/assets), add a line to README.md's Skills list, commit and push to `main`.
2. **Reuse**: at the start of any new task that might relate to past work, look in that repo for a relevant skill first (clone/pull into the scratchpad, read the README index and SKILL.md descriptions) and follow/adapt it; tell the user which skill was used. If none fits, proceed normally.

**Why:** user declared this repo the permanent home for all their skills (2026-10-31) so past analysis methods are reusable across conversations.
**How to apply:** do the repo check before starting domain work (log analysis, reports, dashboards, etc.); a quick `git clone --depth 1` or `git pull` is enough. Pushing is pre-authorized for adding skills to this repo only.
