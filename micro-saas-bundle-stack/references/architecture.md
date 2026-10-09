# Architecture: the single-file bundle frontend

This is the format proven in production by **Portal CEMEC**
(github.com/hugoleopires-bit/portal-cemec, branch `vercel-standalone-bundle`,
file `vercel-standalone/index.html`) — an internal events/contracts
management SaaS that's been extended through dozens of shipped PRs using
exactly this pattern, with zero build-tool breakage.

## Why single-file, no bundler

A normal SPA needs a build step (Webpack/Vite/etc.) before anything is
deployable. For a solo-maintained micro-SaaS that gets iterated on constantly
via chat-driven requests, that build step is pure friction: every edit needs
a build, the build can fail for reasons unrelated to your change, and you
need a build server or CI. The single-file bundle sidesteps all of that —
the file you edit (almost) is the file you deploy. What stands between them
is a thin JSON encode/decode, not a compiler.

## The file's anatomy

`index.html` has three parts:

```html
<!doctype html>
<html>
  <head>...</head>
  <body>
    <div id="root"></div>
    <script type="__bundler/manifest">{"<uuid>":{"data":"<base64>","compressed":true}, ...}</script>
    <script type="__bundler/template">"<!doctype html>...the ENTIRE page as one JSON string..."</script>
  </body>
</html>
```

- **`__bundler/manifest`** — a JSON object mapping UUIDs to binary blobs
  (base64, optionally gzip-compressed). Typically holds one entry: the
  bundled JS runtime (React + the templating compiler), referenced from
  inside the template via `<script src="<uuid>">`. You almost never touch
  this by hand — `scripts/repack_bundle.py` copies it through unchanged.
- **`__bundler/template`** — a JSON *string* containing the page's full
  HTML, including a `<script data-dc-script>` with your application code.
  This is where you'll do 100% of your editing — but you can't just open
  `index.html` and edit it in place, because it's JSON-escaped onto one
  giant line. **Always extract it first** with `scripts/extract_bundle.py`,
  edit the resulting `template.html`, then repack with
  `scripts/repack_bundle.py`. See `references/dev-loop.md` for the full
  loop and why diff-verification matters here specifically.

## The templating DSL

Inside the extracted `template.html`, the markup uses a small set of custom
elements and a `{{ expr }}` interpolation syntax, compiled at runtime (by
the bundled runtime script) into `React.createElement` calls:

| Syntax | Meaning |
|---|---|
| `{{ nome }}` | interpolates a value from the render payload |
| `<sc-if value="{{ cond }}" hint-placeholder-val="{{ false }}">...</sc-if>` | conditional render. The `hint-placeholder-val` is a loading-state hint, not logic — always include it, matching the typical value of `cond` before data loads. |
| `<sc-for list="{{ items }}" as="x" hint-placeholder-count="3">...</sc-for>` | loop. `hint-placeholder-count` is a skeleton-loading hint. |
| `<sc-raw-select value="{{ v }}" sc-camel-on-change="{{ setV }}">...</sc-raw-select>` | a native `<select>`, since a plain `<select>` with React-style controlled `value` needs special handling. |
| `sc-camel-on-click="{{ handler }}"`, `sc-camel-on-change="{{ handler }}"` | event binding — `sc-camel-on-X` maps to the DOM's `onX`. |
| `style="{{ obj }}"` on a React-rendered element accepts a camelCase style **object** (`{ color: '#fff', fontWeight: 600 }`), not a CSS string — the compiler treats it like JSX `style={...}`. On static markup it's a literal CSS string. Don't mix the two up when you add a new computed style. |

## The Component class

The inline `<script data-dc-script>` holds one JS class (conventionally
named `Component`) with:

- **`render()`** (or an equivalent main method) that reads `this.state`,
  computes everything the template needs — derived lists, formatted
  strings, filtered/sorted rows, per-row click handlers — and returns one
  big object. Every `{{ x }}` in the template resolves against this
  object's keys.
- **`this.setState(patch)`** — the only way state changes; a patch object
  or an updater function `(prevState) => patch`, same shape as React's
  class `setState`.
- **`this.h(key, fn)`** — a **permanent memoization** helper for event
  handlers: the first `fn` registered under `key` is cached forever, so
  later renders with the same `key` reuse the same function reference
  (important for the diffing underneath to not re-bind listeners every
  render). This is only safe when `key` fully encodes everything that
  varies — e.g. `this.h('del_' + rowId, () => ...)` is fine because the
  closure captures `rowId` which doesn't change for that key, and the body
  reads `this.state` fresh at call time rather than closing over stale
  values. Getting this wrong (keying by something that *should* vary, or
  closing over a value that goes stale) is the single most common subtle
  bug in this architecture — see `references/dev-loop.md`'s validation
  section.

## Generic patterns worth copying directly into a new project

These recurring patterns, lifted straight from Portal CEMEC, save you from
re-deriving them:

- **Generic entity editor**: one `entCfg(entity)` method returning
  `{ rotulo, fields, defaults, toForm, fromForm }` per entity type, one
  `abrirEditor(entity, index)` / `salvarEditor()` pair that handles
  create+edit for *every* entity through the same modal and the same big
  `setState` updater — instead of a bespoke form component per entity.
- **Shared list-page ("tabelas simples") system**: one generic table
  renderer driven by a config object (`{ titulo, sub, btn, ent, cols, grid,
  rows }`) reused across every "list of X with search/filter/edit/delete"
  screen, instead of one React component per list.
- **Confirmation idiom**: `window.confirm()` / `window.alert()` /
  `window.prompt()` for simple binary decisions and clipboard-copy
  fallbacks, instead of building a custom modal component for every
  "are you sure?" — cheap, no extra state to manage, good enough for an
  internal tool's UX bar.
- **Draft-then-commit for live-updating fields**: when an `onChange`
  handler needs to do something consequential (a confirm dialog, a network
  write) you do NOT want it firing on every keystroke. Keep the typed value
  in a small local draft object in state, only commit (and run the
  consequential logic) on an explicit save action. Wiring a confirm dialog
  straight to a text input's `onChange` is a bug, not a design choice —
  it'll fire per keystroke.
