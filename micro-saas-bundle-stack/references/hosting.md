# Hosting: Vercel, deployed by `git push`

Because the frontend is one static HTML file and there's no build step,
hosting is close to the simplest case Vercel supports: serve the file as a
static asset, plus a couple of serverless functions if you need any
server-side logic Supabase's client SDK can't do directly from the browser
(it usually can — most writes go straight from the browser to Supabase
with the anon key and row-level security, so `api/` often stays minimal
or even empty).

## Minimum project layout

```
your-project/
├── index.html          # the bundle (or vercel-standalone/index.html if you nest it)
├── backend.js           # thin API layer: wraps Supabase calls the frontend calls into
├── vercel.json
├── package.json
└── api/                 # optional: serverless functions, only if you need server-side logic
```

## `vercel.json`

For a pure static file with no routing needs:

```json
{
  "version": 2,
  "buildCommand": null,
  "outputDirectory": "."
}
```

If `index.html` lives in a subdirectory (Portal CEMEC keeps everything
under `vercel-standalone/` so the repo can hold other things alongside
it), set `outputDirectory` to that subdirectory, or point the Vercel
project's **Root Directory** setting at it instead — either works, pick
one and don't fight between them.

## `package.json`

Only needed if you have `api/` functions with dependencies (e.g. the
`@supabase/supabase-js` client for server-side calls). If everything is
client-side (the browser imports `supabase-js` from a CDN `<script>` tag
inside the bundle itself), you may not need a `package.json` at all.

```json
{
  "name": "your-project",
  "private": true,
  "dependencies": {
    "@supabase/supabase-js": "^2"
  }
}
```

## Connecting the project

1. Create the GitHub repo first (see `references/dev-loop.md`'s "First
   commit" section) and push an initial commit — Vercel's "Import
   repository" flow needs something to point at.
2. In Vercel, **New Project → Import** the GitHub repo. Set the **Root
   Directory** if your bundle isn't at the repo root.
3. Set environment variables for the Supabase connection
   (`SUPABASE_URL`, `SUPABASE_ANON_KEY` or whatever names your `backend.js`
   expects) — get these via `mcp__Supabase__get_project_url` and
   `mcp__Supabase__get_publishable_keys`. These go in Vercel's project
   settings, not committed to git.
4. Pick your **production branch**. Portal CEMEC deliberately does NOT use
   `main` for this — it uses a dedicated branch (e.g.
   `vercel-standalone-bundle`) as the one Vercel watches for production
   deploys, keeping `main` free for anything else (or simply not existing).
   Whatever you choose, every feature branch in the dev loop is created
   FROM this branch and PRs target it.
5. First push to that branch triggers the first deploy. Vercel gives you
   a `*.vercel.app` URL immediately; attach a custom domain later if
   needed, same project.

## After that, deploys are automatic

Every merge into the production branch redeploys with no further action.
The one recurring gotcha: a user reporting "my change didn't show up" is
almost always **browser cache**, not a failed deploy, since this is a
single static HTML file browsers are happy to cache aggressively —
confirm the merge actually landed (`git log origin/<prod-branch>`) before
suspecting the deploy pipeline, and suggest a hard refresh
(Ctrl+Shift+R / Cmd+Shift+R) first.
