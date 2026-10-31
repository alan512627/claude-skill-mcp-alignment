# Full Implementation Reference

Complete annotated code for all major functions. Read this when building from scratch or doing major refactors.

---

## parseFile(file, slot)

Reads xlsx via FileReader → binary → XLSX.read → sheet_to_json (header:1). Calls `autoDetectSchema()` then `extract()`. Updates slot card UI and calls `checkReady()`.

```js
function parseFile(file, slot) {
  const reader = new FileReader();
  reader.onload = ev => {
    const wb = XLSX.read(ev.target.result, { type: 'binary' });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const raw = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
    const schemaMap = autoDetectSchema(raw);
    Object.assign(S.schema, schemaMap);
    const data = extract(raw, S.schema);
    S[slot] = { file, raw, data };
    // update UI...
  };
  reader.readAsBinaryString(file);
}
```

---

## autoDetectSchema(raw)

Scans row 3 (or row 0 as fallback) for header keywords. Returns partial schema map.

```js
function autoDetectSchema(raw) {
  const headers = (raw[3] || raw[0] || []).map(h => String(h).toLowerCase());
  const rules = [
    { key: 'level',    kw: ['level'] },
    { key: 'compType', kw: ['component type', 'component'] },
    { key: 'mspn',     kw: ['mspn', 'hw component mspn', 'part number'] },
    { key: 'hwDesc',   kw: ['description', 'hw component description'] },
    { key: 'fwType',   kw: ['fw type', 'firmware type', 'type'] },
    { key: 'swVer',    kw: ['sw version', 'version', 'firmware version', 'fw version'] },
    { key: 'pkgId',    kw: ['package id', 'pkg', 'package'] },
  ];
  const map = {};
  rules.forEach(r => {
    for (const kw of r.kw) {
      const idx = headers.findIndex(h => h.includes(kw));
      if (idx !== -1) { map[r.key] = idx; break; }
    }
  });
  return map;
}
```

---

## extract(raw, schema)

Detects recipeId and version from first 4 rows. Finds data start row (first row where fwType column is non-empty and not a header label). Returns `{ recipeId, version, rows[] }`.

```js
function extract(raw, schema) {
  let recipeId = '?', version = '?';
  // scan rows 0-3 for 'fw recipe id' / 'version' labels
  // fallback: raw[1][2] = recipeId, raw[1][1] = version

  let startRow = 4;
  for (let i = 3; i < Math.min(raw.length, 8); i++) {
    const v = String((raw[i] || [])[schema.fwType] || '').trim().toLowerCase();
    if (v && v !== 'fw type' && v !== 'firmware type') { startRow = i; break; }
  }

  const rows = [];
  for (let i = startRow; i < raw.length; i++) {
    const r = raw[i] || [];
    const fwType = String(r[schema.fwType] || '').trim();
    if (!fwType) continue;
    rows.push({
      level: String(r[schema.level] || '').trim(),
      compType: String(r[schema.compType] || '').trim(),
      mspn: String(r[schema.mspn] || '').trim(),
      hwDesc: String(r[schema.hwDesc] || '').trim(),
      fwType,
      swVer: String(r[schema.swVer] || '').trim(),
      pkgId: String(r[schema.pkgId] || '').trim(),
    });
  }
  return { recipeId, version, rows };
}
```

---

## runCompare()

Builds map from both files supporting duplicate keys (array per key). Iterates A in original order, matches B by key+occurrence index. Then iterates B to find unmatched rows (new-b). Injects `type:'section'` rows when component group changes.

```js
function buildMap(rows) {
  const map = {};
  rows.forEach(r => {
    const k = makeKey(r);
    if (!map[k]) map[k] = [];
    map[k].push(r);
  });
  return map;
}

// In runCompare():
const seenKeys = new Set(); // tracks occurrence count per key
a.data.rows.forEach(rowA => {
  const key = makeKey(rowA);
  const usedCount = [...seenKeys].filter(k => k === key).length;
  seenKeys.add(key);
  const rowB = (mapB[key] || [])[usedCount] || null;
  // determine status, push to result
});
```

---

## calcSeverity(vA, vB, status)

```js
function splitVer(v) {
  return v.replace(/[_\-]/g, '.').split('.').map(s => s.trim());
}
function calcSeverity(vA, vB, status) {
  if (status === 'same')    return 'same';
  if (status === 'missing') return 'missing';
  if (status === 'new-b')   return 'new';
  const pa = splitVer(vA), pb = splitVer(vB);
  if (pa[0] !== pb[0]) return 'major';
  if (pa[1] !== pb[1]) return 'minor';
  return 'patch';
}
```

---

## charDiff(a, b)

Returns `[htmlA, htmlB]` with `<span class="ver-diff-part">` wrapping changed segments.

```js
function charDiff(a, b) {
  if (!a || !b || a === b) return [esc(a||'—'), esc(b||'—')];
  const tokA = tokenize(a), tokB = tokenize(b);
  const lcsResult = lcs(tokA, tokB);
  // walk lcsResult, wrap non-matching tokens in ver-diff-part spans
}
function tokenize(s) {
  return s.match(/[^.\-_]+|[.\-_]/g) || [s];
}
```

---

## exportPDF()

Full flow:
1. Build `printWrap` div (off-screen, `position:absolute; left:-9999px; width:2480px`)
2. Inject header with summary cards (6 stat cards matching web UI)
3. Build HTML table — skip `severity === 'new'` rows; inject section headers lazily
4. `document.body.appendChild(printWrap)`
5. `await new Promise(r => setTimeout(r, 400))` — font render wait
6. Measure all `<tr>` positions with `getBoundingClientRect()` relative to `printWrap`
7. `html2canvas(printWrap, { scale:1, width:2480, windowWidth:2480 })`
8. `document.body.removeChild(printWrap)`
9. Build `cutPoints[]` array using row-aware algorithm (see SKILL.md)
10. For each page slice: create offscreen canvas, `ctx.drawImage(fullCanvas, 0, sliceY, ...)`, `doc.addImage(..., 'JPEG', 0.92)`
11. `doc.save(...)`

**Summary cards HTML pattern:**
```js
const cards = [
  { n: totalItems, label:'TOTAL ITEMS',    color:'#0ff'    },
  { n: diffCnt,    label:'VERSION DIFF',   color:'#f5c842', bar:true },
  { n: sameCnt,    label:'IDENTICAL',      color:'#39d98a' },
  { n: missCnt,    label:'ONLY IN A',      color:'#ff7b29' },
  { n: newBCnt,    label:'NEW IN B',       color:'#4d9fff' },
  { n: majCnt,     label:'MAJOR UPGRADES', color:'#0ff'    },
].map(c => `
  <div style="flex:1;background:#0f1520;border:1px solid #1c2a3e;border-radius:8px;padding:18px 20px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;height:2px;background:${c.color};"></div>
    <div style="font-family:Syne,sans-serif;font-size:36px;font-weight:800;color:${c.color};line-height:1;margin-bottom:8px;">${c.n}</div>
    <div style="font-size:11px;color:#5a7591;letter-spacing:1.5px;text-transform:uppercase;">${c.label}</div>
    ${c.bar ? `<div style="height:3px;background:#1c2a3e;margin-top:10px;overflow:hidden;border-radius:2px;"><div style="height:100%;background:${c.color};width:${totalItems ? Math.round(c.n/totalItems*100) : 0}%;"></div></div>` : ''}
  </div>
`).join('');
```

---

## Timeline (multi-file)

Slots are dynamically created. Each loaded file is stored in `S.tlFiles[idx]`. On `runTimeline()`:
- Build `fwMap`: key (`compType / fwType`) → array of `{ recipeId, swVer }` per file
- Filter to keys where `new Set(versions).size > 1`
- Render as list of changed FW items with version chips per recipe

---

## CSS Variables

```css
:root {
  --bg: #07090f;  --bg2: #0d1117;
  --surface: #0f1520;  --surface2: #141d2b;  --surface3: #1a2538;
  --border: #1c2a3e;  --border2: #243447;
  --cyan: #0ff;  --orange: #ff7b29;  --green: #39d98a;
  --yellow: #f5c842;  --red: #ff4d6a;  --blue: #4d9fff;
  --text: #cdd9e5;  --text-dim: #5a7591;  --text-muted: #2d3f54;
  --mono: 'IBM Plex Mono', monospace;
  --sans: 'Syne', sans-serif;
}
```

---

## Common Pitfalls

| Issue | Cause | Fix |
|---|---|---|
| Clicking upload freezes UI | `input[type=file]` overlaid on card with `position:absolute` | Move input to DOM with `display:none`, trigger via `onclick → input.click()` |
| PDF is all black / no text | `visibility:hidden` on printWrap | Use `position:absolute; left:-9999px` instead |
| PDF text too small | printWrap too narrow (e.g. 1560px) → scaled down to fit A3 | Use `width:2480px` (A3 @ 150dpi), font-size 13px |
| Rows cut at page boundaries | Fixed-pixel slicing | Use row-aware cut points from `getBoundingClientRect()` measurements |
| Duplicate FW key silently dropped | Map overwrites on same key | Use array-per-key map, match by occurrence index |
| `autoTable` width warning | cellPadding × cols exceeds page width | Use `html2canvas` approach instead of autoTable |
