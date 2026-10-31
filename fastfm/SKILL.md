---
name: "fastfm"
description: "Working rules for the FastFM project (Tauri 2 Windows file manager, Rust + vanilla JS). Invoke at the START of any session that will read or modify FastFM — it carries the editing constraints, verification gate, scope discipline, the one-place-then-confirm rollout rhythm, the pitfall index, and how this user expects to work, all of which prevent repeating known mistakes."
---

# FastFM — project working rules

Tauri 2 desktop file manager for Windows. Rust backend (`src-tauri/src/*.rs`) + vanilla-JS frontend (`src/main.js`, `src/styles.css`). No framework, no bundler.

Project root: `C:\Users\dicky\Downloads\FastFM`
In the Linux sandbox: `/sessions/<session>/mnt/Downloads/FastFM`

Read `HANDOFF.md` in the project root for the full picture. This skill is the subset you must never get wrong.

---

## 1. Scope discipline — touch only what was asked

**Do not change anything that was not requested.** No opportunistic refactors, no reformatting, no "while I'm here" improvements to adjacent code or comments.

**One exception, and it requires permission first:** when the requested change *necessarily* collides with an existing rule or behaviour and cannot be done without altering it — **stop, explain the collision, why it is unavoidable, and what the options are. Wait for the user's decision before editing.** Never decide unilaterally that the new way is better.

Typical collisions: a new layout requirement versus an existing CSS constraint (a `max-width` blocking a new drag range); a shared function whose signature must change but has other callers; a bug fix whose correct form changes an established default.

Order is **explain → confirm → edit**, never edit-then-justify.

(Rewriting a regression check that asserted an old string literal is *not* this kind of collision — that is the check catching up with behaviour, see §5. Changing the *behaviour* itself is.)

## 2. Editing — never use the Edit tool on this project

This mount **truncates files on write** (it once cut the tail off `archive.rs`). Every edit goes through bash + a Python heredoc with a uniqueness guard:

```bash
cd /sessions/<session>/mnt/Downloads/FastFM && python3 - <<'PY'
p='src/main.js'; s=open(p,encoding='utf-8').read()
old = """<enough surrounding context to be unique>"""
new = """<replacement>"""
assert s.count(old)==1, f"anchor matched {s.count(old)}x"
s = s.replace(old, new)
open(p,'w',encoding='utf-8',newline='\n').write(s)
print('ok')
PY
```

- `assert s.count(old)==1` **before** writing. A failed assert is a good outcome — nothing was corrupted; report "nothing was written" rather than retrying blindly.
- Read with Python's default text mode (universal newlines) so `\n` anchors match CRLF files; restore CRLF with `sed -i 's/\r$//' f && sed -i 's/$/\r/' f`.
- `.bat` / `.cmd` / `.ps1` must be **CRLF + pure ASCII** (`file f`, `grep -Pn '[^\x00-\x7F]' f`).
- If `rm` fails with "Operation not permitted", call `allow_cowork_file_delete` rather than leaving a stub.

## 3. Verification gate — run all three, every time

```bash
node --check src/main.js          # JS syntax
node scripts/contract_check.mjs   # every invoke()d command is registered in lib.rs
node scripts/checks.mjs           # 430+ regression assertions
```

Only report success when all three pass. **There is no Rust compiler in the sandbox** — `cargo` does not exist. Rust changes cannot be verified here; say so plainly and let the user build. For Rust, at minimum check brace/paren balance and that every struct literal was updated when a field was added.

Add an assertion to `checks.mjs` for every bug fixed and every feature added.

## 4. Rolling a change out across the four list views

The same change usually applies to several views: main file list, preview pane, archive popup (`openArchive`), SFTP list (`rlist`). **Do not do all four at once.**

1. Implement in **one** place.
2. Run the gate, then **stop and wait for the user's compile check**.
3. Once verified, **proactively list the other places the same rule applies and ask whether to propagate.**
4. Only spread on confirmation. If declined, note in `HANDOFF.md` that the narrower scope is deliberate.

This is the user's explicit process, born from two failures: a name-column scrollbar shipped to the popup but not SFTP, and later a "only the name column scrolls" rule applied to the preview pane while the popup and SFTP still scrolled the whole table. Both times the user had to ask "did the others follow?".

When asked whether other views followed, **check the code with grep and present a table** — never answer from memory.

## 5. Assert behaviour, not string literals

A check that greps for a hard-coded snippet **passes while the bug is live**:

```js
// BAD — stayed green while tar timestamps were 8 hours wrong
ok(/pvDateCell\(a\.mtime, true\)/.test(M), 'timestamps render correctly');

// GOOD — fails if the decision logic disappears
ok(/function archiveTsIsWallClock/.test(M) && /chain\[chain\.length - 1\]/.test(M),
   'UTC-vs-local chosen per container, innermost archive wins');
```

When a fix makes an existing check fail, first ask whether the check asserted a literal. Usually it did — rewrite it to assert the new behaviour instead of reverting the fix.

## 6. Trace data end to end after any schema change

Backend correct + renderer correct is not enough. Intermediate functions that rebuild objects silently drop fields:

```js
files.push({ label: rest, name, size: en.size, is_dir: false });  // mtime lost here
```

This bug shipped twice — once in the file branch, once in the folder branch one line below. After adding a field, grep every `.map()`, object literal, spread and destructure between source and DOM.

## 7. Command contract (frontend ↔ backend)

- JS passes **camelCase**, Rust receives **snake_case** (`destDir` → `dest_dir`).
- A new command must be added to `generate_handler!` in `lib.rs` or `contract_check.mjs` fails.
- Long operations use the `op://progress` + `op://done` pattern in `ops.rs` (`op_register` / `op_progress` / `op_done_result`) for a progress modal and working cancel. Reuse it.

## 8. Sync and git

- **Never run git or gh on the user's behalf**, and never handle their credentials. Give them the command.
- The frontend is embedded: JS/CSS changes still require a rebuild.
- `install.bat` aborts early if `fastfm.exe` is running (a locked exe fails linking with `os error 5` after minutes).

## 9. Independent QA review

For anything non-trivial, spawn a **read-only** QA agent after implementing, then a second pass to verify the fixes. Give it the data paths to trace and tell it to judge as a user would. Two rounds found 26 defects here, 6 invisible to the existing checks — and the second round caught a fix that reintroduced the very bug it targeted.

Keep a single writer. Agents analyse; the main thread edits.

## 10. Pitfall index

`HANDOFF.md` §6 lists 44+ pitfalls with root cause and fix; 6A the QA loop, 6B the rollout rhythm, 6C scope discipline. Highest-value:

- 6.35 fields dropped by intermediate object rebuilds
- 6.36 regression checks asserting literals stay green through bugs
- 6.37 zip/7z store zone-less wall clock, tar stores true epoch; `.tar.bz2`/`.tar.xz` route through 7z, not tar
- 6.38 CSS custom properties inherit downward only — siblings do not see them
- 6.39 inline `style="width:100%"` silently defeats a stylesheet's `width:max-content`
- 6.40 row indices break as identifiers across a re-sort; anchor on paths
- 6.41 a filter must never hide its own off switch
- 6.42 hiding rows must also deselect them, or they still get deleted
- **flex + `overflow:hidden`**: a flex item's automatic minimum size only protects it while `overflow` is `visible`. `overflow:hidden` makes `min-height:auto` resolve to 0, so the item can collapse to nothing — this silently hid an entire column header.

## 11. Working with this user

**Rhythm — one batch, then the user builds.** There is no cargo in the
sandbox, so nothing is proven until the user compiles. Ship one coherent
change, state exactly what to look at, and stop. Do not stack a second
feature on an unverified first one. When a request contains two independent
features, say which is which so they can be tested apart.

**Verification is theirs to trigger, not yours to declare.** "Done" is not a
thing you announce. Report what the gates say (`checks` / `mutants` /
`contract` / `logic` / `node --check`), name what the user must look at, and
wait. Expect "先 review" and "這樣是符合預期的嗎" — those are the real
acceptance steps. `claude.md` Rule 14 (user-level, outside the repo) requires
an independent review before any commit; §9 above is how that is carried out.

**Never assert what you have not checked.** If you cannot explain something
from the code, say so plainly and say what evidence would settle it. Do not
rank possibilities and present the top one as the cause (HANDOFF 6.73), and
do not claim a platform limitation without having looked for the machinery
first — that claim has been wrong here before.

**Own errors flatly.** Name the defect as yours, in one line, then fix it.
No hedging, no apology spiral. Where the mistake has a class rather than an
instance, guard the class: a missing trait import became a whole-tree
assertion, not a one-line fix.

**Visual work: direction, not pixels.** Requests arrive as a mood — "藏青色",
"靜謐", "apple design", "玻璃光澤". Choose concrete values yourself and say
what each one is for. Theme-agnostic beats a literal colour: `currentColor`
and `inherit` follow whatever the theme decided, a hardcoded `#fff` breaks
the light themes.

**Never let a redesign delete a functional signal.** The failure ring on the
float icon survived "remove all shadows" because it is the only evidence the
user gets that a drag could not start. Guard such signals explicitly, or the
next tidy-up removes them.

**Language.** Reply in Traditional Chinese. Code, comments, and assertion
messages stay in English.

