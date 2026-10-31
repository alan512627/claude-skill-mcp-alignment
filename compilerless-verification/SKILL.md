---
name: "compilerless-verification"
description: "Discipline for shipping correct changes when you cannot compile or run the code — static verification gates, assert-guarded in-place edits, regression checks that assert behaviour instead of string literals, and an independent QA review loop. Use on any project where the toolchain is unavailable, the editor tool is untrustworthy, or a green test suite has been hiding real bugs."
---

# Shipping correct changes without a compiler

For projects where you cannot build or run the code: no toolchain in the sandbox, a mount that corrupts writes, or a test suite that is really a pile of greps. The goal is to make defects **fail loudly at edit time**, since they will not fail at compile time.

---

## 1. Edit with a uniqueness guard, never blind

Do not trust an editor tool that might truncate or fuzzy-match. Use an explicit script that dies before writing if the target is not exactly where you think:

```bash
python3 - <<'PY'
p='path/to/file'; s=open(p,encoding='utf-8').read()
old = """<enough context to be unique>"""
new = """<replacement>"""
assert s.count(old)==1, f"anchor matched {s.count(old)}x"
s = s.replace(old, new)
open(p,'w',encoding='utf-8',newline='\n').write(s)
print('ok')
PY
```

- `assert ... == 1` runs **before** the write. A failed assert means nothing was touched — that is a success, not a setback. Report it as "nothing was written" rather than retrying blindly.
- Multiple edits in one script: assert each anchor. First failure aborts everything.
- Reading with Python's universal newlines turns CRLF into `\n`, so `\n` anchors match; restore line endings afterwards if the file needs CRLF.
- After every edit run whatever cheap syntax check exists (`node --check`, `python -m py_compile`, brace/paren balance counting) plus the project's own gate.

## 2. Assert behaviour, not string literals

This is where grep-shaped test suites betray you. A check that greps for a hard-coded snippet **stays green while the bug is live**:

```js
// BAD — passed the whole time timestamps were 8 hours wrong
ok(/renderDate\(x, true\)/.test(src), 'timestamps render correctly');

// GOOD — fails the moment the decision logic disappears
ok(/function pickTimezoneMode/.test(src) && /innermost/.test(src),
   'timezone chosen per container, innermost wins');
```

Rules of thumb:
- If a rename or refactor would break the check but a **semantic inversion** would not, the check is worthless.
- When a fix makes existing checks fail, ask first whether they asserted literals. Usually they did — rewrite the check to assert the new behaviour rather than reverting the fix.
- Prefer asserting the existence of the *decision* (a function, a branch, a guard) over the shape of one call site.
- Add a check for every bug fixed, phrased as the user-visible symptom it prevents.

## 3. Trace data end to end after any schema change

Correct producer + correct consumer is not enough. Intermediate transforms silently drop fields, and nothing errors:

```js
items.push({ label: x.label, size: x.size });  // the field you just added is gone
```

After adding or renaming a field, grep every `.map()`, object literal, spread and destructure between source and sink. Expect the same bug to exist in a sibling branch a few lines away — it usually does.

## 4. Independent QA review loop

You cannot catch your own blind spots by re-reading your own diff. Spawn a **read-only** reviewer and give it:

- the exact changes made and the intent behind each,
- specific data paths to trace,
- an instruction to judge as a user would ("what would the user SEE go wrong"),
- an instruction to state plainly when a category is clean rather than padding,
- an instruction to separate verified defects from suspicions.

Then run a **second pass to verify the fixes**, explicitly hunting for defects introduced by the fixes themselves. This is not ceremony — in practice the second pass reliably finds fresh regressions, including fixes that reintroduce the very bug they targeted via an over-broad pattern.

Keep exactly one writer. Reviewers analyse; the main thread edits. Concurrent writers plus an untrustworthy editor is how files get corrupted.

## 5. Classic silent-failure patterns to check for

| Pattern | Symptom |
|---|---|
| Row index used as an identifier across a re-sort | Wrong item acted on; no error |
| Filter/hide that does not also deselect | Destructive action hits invisible items |
| A filter whose only "off switch" is hidden when the filter empties the list | User is stranded with no way back |
| CSS custom property set on a node that is a **sibling** of the consumer | Value silently resolves to invalid, layout collapses |
| Inline `style` overriding a stylesheet rule you just added | "I changed it and nothing happened" |
| Expensive call inside a comparator | Sort becomes 10–100× slower |
| An "exclusion list" broader than what the producer actually produces | Reintroduces the bug for the extra cases |

## 6. Report honestly

State explicitly what was verified and what was not. "Checks pass" is not "it works" when the checks are greps and the compiler never ran. Say which parts a human must build or exercise, and name the single change you are least confident about.

