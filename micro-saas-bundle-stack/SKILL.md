---
name: micro-saas-bundle-stack
description: Builds a complete micro-SaaS or internal web tool from zero to a live deploy — git repo, a single-file HTML "bundle" frontend with no build step, a generic Supabase key-value backend, and automatic Vercel hosting — then keeps shipping new features safely through a validated branch-edit-repack-diff-PR loop. This exact stack is proven in ongoing production use on Portal CEMEC (github.com/hugoleopires-bit/portal-cemec, branch vercel-standalone-bundle), an internal events/contracts management system that has shipped dozens of features this way with zero build-tool breakage. Use this skill whenever the user wants to start a new SaaS, micro-SaaS, internal admin tool, or dashboard from scratch — even if they just say "quero criar um app", "preciso de um sistema para gerenciar X", "monta um painel interno", or "build me a tool to track Y" — whenever they want a fast backend without designing a relational schema up front, whenever they mention deploying on Vercel plus Supabase, or whenever they're extending an EXISTING project already built with this single-file-bundle + Supabase-blobs + Vercel pattern (editing a template.html extracted from a bundle, a __bundler/manifest or __bundler/template script, a generic "blobs" table, or debugging a "tag balance" / byte-diff issue on a packed bundle).
---

# Micro-SaaS bundle stack

A complete, opinionated pipeline for building and running a small SaaS or
internal tool with almost no infrastructure to maintain: one HTML file as
the frontend, one generic table as the backend, and `git push` as the
deploy mechanism. It trades the flexibility of a "proper" framework setup
for radically less to break and radically faster iteration — the right
trade for a tool one person (or a small team, working mostly through
chat-driven requests) is going to keep evolving indefinitely.

**Reference implementation**: Portal CEMEC —
github.com/hugoleopires-bit/portal-cemec (branch `vercel-standalone-bundle`,
file `vercel-standalone/index.html`). When in doubt about how a pattern
should look in practice, that repo's commit history is the worked example
— every pattern described here was extracted from real, shipped PRs there,
not designed in the abstract.

## The three pieces

| Piece | What it is | Detail |
|---|---|---|
| Frontend | One `index.html` "bundle": a JSON-encoded template string + an inline Component class, no build step | `references/architecture.md` |
| Backend | Supabase Postgres, one generic `blobs(chave, valor jsonb)` table instead of a hand-designed schema | `references/database.md` |
| Hosting | Vercel, static file + optional minimal `api/`, auto-deploy on push | `references/hosting.md` |

Read each reference file before doing the corresponding setup step below —
they contain the actual SQL, JSON configs, and reasoning; this file is the
orchestrating checklist.

## Zero to first deploy

Do these in order. Each step links to the reference file with the actual
commands/config/SQL — don't skip reading it, the "why" matters for
decisions you'll make later (e.g. which entities get a real table instead
of a blob).

1. **Decide the production branch name.** Don't default to `main` — pick
   a dedicated branch (Portal CEMEC uses `vercel-standalone-bundle`) that
   Vercel watches for deploys, so `main` (if it exists at all) stays free
   for anything else. Every later step targets this branch name.

2. **Create the git repo and first commit.**
   ```bash
   mkdir <project> && cd <project>
   git init
   mkdir -p vercel-standalone/api
   git checkout -b <prod-branch>
   ```
   Create the repo on GitHub (via the GitHub MCP tools available in this
   session, or ask the user to create it and give you the remote URL),
   then `git remote add origin <url>`.

3. **Create the Supabase project and schema.** Call
   `mcp__Supabase__create_project`, then `mcp__Supabase__apply_migration`
   with the `blobs` table and (if you need login) the `app_usuarios` table
   + `hash_senha`/`verificar_senha` RPCs. Full SQL in
   `references/database.md`. Grab the project URL and anon key via
   `mcp__Supabase__get_project_url` / `mcp__Supabase__get_publishable_keys`
   — you'll need them in step 5.

4. **Write the bundle skeleton.** Build a minimal `index.html` with the
   three-part structure (`__bundler/manifest`, `__bundler/template`, the
   Component class) described in `references/architecture.md`. Start
   small: a Component with a `constructor` setting `this.state = {}`, a
   `render()` returning a single "Hello, it's wired up" payload, and the
   templating syntax for at least one `{{ }}` interpolation, one
   `<sc-if>`, and one `<sc-raw-select>` — enough to prove the whole chain
   (state → render payload → template → compiled React) works before you
   build real features on top. Write `backend.js` as the thin layer
   wrapping `sb.from('blobs')...` calls the Component will call into.

5. **Set up Vercel.** `vercel.json`, optionally `package.json`, connect
   the GitHub repo, set the Supabase URL/key as environment variables, set
   the **Root Directory** / **Production Branch** to match step 1-2.
   Full detail in `references/hosting.md`.

6. **First push, first deploy.**
   ```bash
   git add -A && git commit -m "feat: initial bundle skeleton"
   git push -u origin <prod-branch>
   ```
   Confirm the Vercel deploy succeeds and the "Hello, it's wired up" page
   loads at the `*.vercel.app` URL before building anything real on top —
   you want to know the whole chain works end to end while the moving
   parts are still trivial to debug.

From here, every actual feature goes through the development loop below —
never hand-edit the packed `index.html` directly.

## The development loop (every feature, every fix)

Full step-by-step with commands in `references/dev-loop.md`. Summary:

```
branch off <prod-branch>
  → extract_bundle.py          (decode template.html out of the bundle)
  → edit template.html
  → node --check + check_tag_balance.py     (catch syntax/markup breakage
                                              early — there's no compiler
                                              to catch it for you)
  → repack_bundle.py           (re-encode back into the bundle)
  → diff-verify against the pre-edit original (prove the change is
                                              EXACTLY what you intended)
  → commit, push, open a PR against <prod-branch>
  → wait for explicit confirmation before merging — never merge
    automatically, even when you're confident the change is correct
  → (merge → Vercel auto-deploys)
```

The bundled scripts live in `scripts/`: `extract_bundle.py`,
`repack_bundle.py`, `check_tag_balance.py`. They're generic — pass
explicit file paths, nothing in them is specific to any one project.

**The diff-verification step is the one most worth not skipping.** The
packed bundle is one giant JSON-escaped line, so an ordinary `diff` tells
you nothing useful on the packed file directly — `references/dev-loop.md`
has two concrete techniques (common-prefix/suffix extraction for a single
isolated edit, or re-extract-both-and-diff for multiple scattered edits)
that make the verification actually legible. Skipping this is how an
unintended second match of an edited string silently ships.

## When something's wrong with the *data*, not the code

A bug report that turns out to be bad data already sitting in Supabase
(not a code bug) doesn't go through the PR loop — fix it with a direct
`execute_sql` UPDATE, and separately fix whatever code path let the bad
value get written, so it doesn't come back. Detail and a worked SQL
example in `references/database.md`.

## What this stack is (and isn't) good for

Good for: a tool one person or a tiny team maintains and keeps evolving
indefinitely through small, frequent changes — internal admin panels,
ops dashboards, small CRMs, event/registration management, anything where
"ship a fix for a reported bug within the hour" matters more than
textbook architecture.

Reconsider for: anything needing a large team of engineers working in
parallel (the single-file frontend doesn't parallelize across many
simultaneous editors well), heavy client-side compute/offline support
(no code-splitting, everything loads at once), or a public-facing product
needing real Auth flows (social login, email verification, password
reset) out of the box — swap in real Supabase Auth instead of the
lightweight RPC pattern in `references/database.md` for that case.
