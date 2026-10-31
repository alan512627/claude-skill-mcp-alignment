---
name: feedback-c9a17-vera-rubin-vs-ultra
description: Vera Rubin and Vera Rubin Ultra are separate projects — file into separate subfolders within C9A17
type: feedback
project: Local-C9A17
---

"Vera Rubin" and "Vera Rubin Ultra" are different project documents — never merge them. Within each document-type folder under `Document\Nvidia\` (e.g. TechnicalOverview, QuickStartGuide, FW_EAS), create two subfolders: `VeraRubin\` and `VeraRubinUltra\`, and file each document by its product line.

**Why:** User corrected this after both were dumped into the same type folder.

**How to apply:** Filenames containing the literal word "Ultra" go to `VeraRubinUltra\`; otherwise `VeraRubin\`. When creating a type folder, create both subfolders up front. Reflect this in the HTML change-list report. See [[feedback_c9a17_dedup_rule]].
