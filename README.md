# claude-skills

Reusable Claude Code skills — standalone pipelines/workflows, not tied to
any one project. Each top-level directory is one skill (a `SKILL.md` plus
its bundled scripts/references).

## Skills

- **[micro-saas-bundle-stack](micro-saas-bundle-stack/)** — builds a
  micro-SaaS / internal web tool from zero to a live deploy: a single-file
  HTML "bundle" frontend (no build step), a generic Supabase key-value
  backend, and automatic Vercel hosting, plus the recurring
  branch→edit→repack→diff→PR loop to keep shipping features safely.
  Proven in production on
  [Portal CEMEC](https://github.com/hugoleopires-bit/portal-cemec)
  (branch `vercel-standalone-bundle`).
