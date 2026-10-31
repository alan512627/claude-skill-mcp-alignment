---
name: feedback-c9a17-dedup-rule
description: Dedup rule for the C9A17 Downloads-monitoring workflow — when to skip moving a file already present in the project folder
type: feedback
project: Local-C9A17
---

When monitoring the Downloads folder for C9A17 / Yosemite / Vera Rubin Ultra* files and a same-named file already exists somewhere in `D:\Projects\C9A17`, only skip moving/copying it if BOTH hold:

1. Content is fully identical (checksum, e.g. md5sum — not just size or name).
2. The version number in the filename also matches exactly (e.g. "v0.8" vs "v0.8", not "v0.9").

**Why:** User explicitly corrected the dedup logic — name or content match alone isn't sufficient; version drift must be ruled out too.

**How to apply:** Before skipping a Downloads file as "already in project", run a checksum comparison AND compare the version token in both filenames. If either fails or is ambiguous (no clear version token), do NOT bypass — move/copy it in and flag the ambiguity in the change-list report. Applies to the recurring task: monitor Downloads → sort into type folders in C9A17 → produce tabbed HTML report.
