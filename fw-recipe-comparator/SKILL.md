---
name: fw-recipe-comparator
description: Build a firmware recipe comparison web tool as a single-file HTML app. Use this skill whenever the user wants to compare firmware versions across Excel recipe files, build a FW diff viewer, create a firmware version tracker, or needs to compare hardware component SW versions between two recipe IDs. Also trigger this skill when the user asks to update, fix, or extend an existing FW Recipe Comparator tool — even if they just say "add a feature to the comparator" or "fix the PDF export". The output is always a standalone .html file with no external dependencies beyond CDN libraries.
---

# FW Recipe Comparator Skill

Builds a **single-file HTML firmware recipe comparison tool** for Azure GPU Compute / hardware validation workflows. The tool ingests Excel-based FW recipe files, compares SW versions component-by-component, and produces an interactive diff table with PDF and Excel export.

## Output

Always a single self-contained `.html` file saved to `/mnt/user-data/outputs/`. No build step, no server — opens directly in the browser.

## Excel File Format

FW Recipe xlsx files follow this structure:
- **Row 0**: Column header labels
- **Row 1**: Metadata — `version` in col 1, `recipe ID` in col 2
- **Rows 2–3**: Additional header / blank
- **Row 4+**: Data rows with columns:
  - Col 0: `Level`
  - Col 1: `Component Type`
  - Col 2: `HW Component MSPN`
  - Col 3: `HW Component Description`
  - Col 4: `FW Type`
  - Col 5: `SW Version`
  - Col 6: `Package ID`

> The tool auto-detects column positions by scanning header keywords, and provides a manual override UI panel.

## Core Libraries (all via CDN)

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
```

## Architecture

### State Object
```js
const S = {
  a: null, b: null,     // loaded file data for baseline and compare
  rows: [],             // compared rows (type:'section' | type:'data')
  tlFiles: [],          // timeline mode files
  filter: 'all',        // active filter chip
  sort: 'default',      // active sort
  schema: {             // column index mapping (0-based)
    level:0, compType:1, mspn:2, hwDesc:3, fwType:4, swVer:5, pkgId:6
  }
}
```

### Data Row Structure
Each `type:'data'` row in `S.rows`:
```js
{
  type: 'data',
  rowA: { level, compType, mspn, hwDesc, fwType, swVer, pkgId } | null,
  rowB: { ... } | null,
  swB: string,
  pkgB: string,
  status: 'same' | 'diff' | 'missing' | 'new-b',
  severity: 'same' | 'patch' | 'minor' | 'major' | 'new' | 'missing'
}
```

### Compare Key
Rows are matched by: `Level + ComponentType + MSPN + FWType`

Duplicate keys are handled sequentially (matched by occurrence order), so duplicate FW entries are not silently dropped.

### Severity Rules
Versions are split by `.` `-` `_` delimiters:
- Segment 0 differs → `major`
- Segment 1 differs → `minor`
- Segment 2+ differs → `patch`
- B-only entry → `new`
- A-only entry → `missing`

## UI Structure

```
Header
Tabs: [⇌ 雙檔比對] [↗ 多版 Timeline] [? 使用說明]

── Tab: 雙檔比對 ──────────────────────────────────
Upload slots (A = Baseline, B = Compare)
Schema mapper panel (auto-detected, manual override)
Action bar: [⚡ 執行比對] [↓ Excel] [↓ PDF] [↺ 重置]
Stats strip: Total / Version Diff / Identical / Only in A / New in B / Major Upgrades
Filter chips: 全部 / ⚠ 差異 / + B新增 / − A獨有 / ✓ 相同
Sort select + search input
Result table (11 columns, section headers, color-coded rows)

── Tab: 多版 Timeline ─────────────────────────────
N upload slots (dynamic, add more button)
Timeline output: FW items with version changes across recipes

── Tab: 使用說明 ──────────────────────────────────
Severity legend + compare key explanation
```

## Critical Implementation Details

### File Input (avoid hang bug)
**Never** use `<input type="file">` with `position:absolute; inset:0` overlaying a card — this causes UI freeze on `file://` protocol in Chrome/Edge.

✅ Correct pattern:
```html
<input type="file" id="file-input-a" class="slot-file-input" style="display:none" onchange="loadSlot(event,'a')">
<div class="slot" onclick="document.getElementById('file-input-a').click()">...</div>
```

### Char-level Version Diff
Use LCS (Longest Common Subsequence) on tokenized version segments to highlight exactly which segment changed:
```js
function tokenize(s) { return s.match(/[^.\-_]+|[.\-_]/g) || [s]; }
```
Wrap changed segments in `<span class="ver-diff-part">` with yellow background.

### Bidirectional Compare
After iterating A→B, also detect B-only rows (status: `'new-b'`). These get `rowA: null` and a green left border.

### Schema Auto-detection
```js
const rules = [
  { key: 'fwType', kw: ['fw type', 'firmware type', 'type'] },
  { key: 'swVer',  kw: ['sw version', 'version', 'firmware version'] },
  // ...
];
// Scan header row for keyword matches → set column index
```

## PDF Export

Use **html2canvas** to capture a dynamically built off-screen HTML table (not autoTable). This ensures pixel-perfect match with the web UI styling.

### Key PDF rules
1. **Off-screen element**: Use `position:absolute; left:-9999px` — NOT `visibility:hidden` (html2canvas won't capture hidden elements)
2. **Print table width**: `2480px` (= A3 landscape @ 150dpi) — font size 13px renders clearly
3. **Row-aware page breaking**: Measure all `<tr>` positions with `getBoundingClientRect()` BEFORE capture, then find cut points at row boundaries to avoid splitting rows across pages
4. **No footer text**: Do not add page numbers or footer text — they overlap content
5. **Exclude `severity === 'new'`** rows from PDF output
6. **Summary cards**: Include stats strip at top of PDF matching the web UI cards

### Row-aware slicing algorithm
```js
// Measure row bounds relative to printWrap before capture
const wrapTop = printWrap.getBoundingClientRect().top + window.scrollY;
const rowBounds = allTrs.map(tr => {
  const rect = tr.getBoundingClientRect();
  return {
    top:    rect.top    + window.scrollY - wrapTop,
    bottom: rect.bottom + window.scrollY - wrapTop
  };
});

// Build cut points: find last row.bottom <= pageFloor + PAGE_H_PX
const cutPoints = [0];
let pageFloor = 0;
while (true) {
  const nextCeil = pageFloor + PAGE_H_PX;
  if (nextCeil >= canvas.height) break;
  let cutY = nextCeil;
  for (let i = rowBounds.length - 1; i >= 0; i--) {
    if (rowBounds[i].bottom <= nextCeil && rowBounds[i].bottom > pageFloor) {
      cutY = Math.ceil(rowBounds[i].bottom);
      break;
    }
  }
  cutPoints.push(cutY);
  pageFloor = cutY;
}
cutPoints.push(canvas.height);
```

## Excel Export

Use `XLSX.utils.aoa_to_sheet()`. Output **only `type:'data'` rows** — skip section header rows entirely.

```js
S.rows.forEach(r => {
  if (r.type !== 'data') return; // skip section headers
  // push row data...
});
```

## Visual Design

Dark terminal/cyberpunk aesthetic:
- Background: `#07090f`, surface: `#0f1520`
- Accent cyan: `#0ff`, orange: `#ff7b29`, green: `#39d98a`, yellow: `#f5c842`, red: `#ff4d6a`
- Font: IBM Plex Mono (mono) + Syne (headings)
- Diff rows: yellow left border `3px solid #f5c842` + `rgba(245,200,66,0.06)` bg
- New-B rows: green left border + `rgba(57,217,138,0.04)` bg
- Missing rows: orange left border + `rgba(255,123,41,0.04)` bg
- Section headers: cyan text on `rgba(0,255,255,0.07)` bg
- Scanline overlay via `body::after` repeating gradient
- Corner bracket decorations (fixed, `position:fixed`)
- Clip-path polygon on buttons for chamfered corner effect

## Reference Files

- `references/full-implementation.md` — Complete annotated JS for all major functions (compare engine, timeline, schema detection, export). Read this when building from scratch or doing major refactors.
