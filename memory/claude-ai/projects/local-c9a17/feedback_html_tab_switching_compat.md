---
name: feedback-html-tab-switching-compat
description: "Standalone HTML reports for this user: tab switching must use plain CSS sibling combinators — not JS click handlers and not :has()"
type: feedback
project: Local-C9A17
---

For multi-tab standalone HTML files (e.g. the C9A17 folder-report dashboard), do not rely on `<script>` click handlers or `:has()` for tab switching — both failed silently in the user's preview environment ("沒反應"; then "你把其它二個分頁都隱藏了").

**How to apply:** Put hidden `<input type="radio">` elements as direct children of `<body>` (shared `name`, first `checked`), followed by the tab-label bar (`<label for="...">`) and the content container — all direct children of `<body>`, in that order. Drive visibility with `#tab-x:checked ~ .tabs label[for="tab-x"]` and `#tab-x:checked ~ main #panel-x { display:block; }`. Verify DOM order (radios → tab bar → content) whenever reused.
