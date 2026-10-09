# The development loop

This is the loop to run for **every single feature or fix**, once the
project is scaffolded and deployed (see `SKILL.md` for the zero-to-deploy
steps). It's what makes "no build step, no parser in the loop until the
browser" safe to iterate on quickly instead of risky — every step exists
to catch a specific class of mistake before it ships, because none of the
normal safety nets (a compiler, a bundler, a linter wired into the build)
exist here by default.

Run `scripts/extract_bundle.py` and `scripts/repack_bundle.py` from
wherever you've copied this skill's `scripts/` directory — pass explicit
paths, there's nothing project-specific hardcoded in them.

## 1. One branch per request

```bash
git fetch origin <prod-branch>
git checkout -B claude/<short-description> origin/<prod-branch>
```

Don't stack unrelated changes on one branch. If you're mid-task on branch A
and the user asks for something unrelated, start branch B from the
production branch fresh — don't improvise on top of A's uncommitted state.

## 2. Extract

```bash
python3 scripts/extract_bundle.py vercel-standalone/index.html /tmp/work
```

This decodes `template.html` out of the bundle so you have real,
multi-line HTML to read and edit (see `references/architecture.md` for
what's inside it). Re-extract fresh at the start of every branch — don't
reuse a stale extraction from a previous task, since the production branch
may have moved (another session may have merged something) since you last
looked.

## 3. Edit

Make the smallest change that satisfies the request. Reuse the project's
existing patterns (the generic entity editor, the shared list-page system,
the confirm-gate idiom — see `references/architecture.md`) instead of
inventing a parallel way to do the same thing. Before assuming a pattern
doesn't exist yet, grep for it — these codebases accumulate exactly these
kinds of reusable primitives over time, and duplicating one is a wasted
diff.

## 4. Validate — before you trust the edit

Two checks, in this order:

**a. Syntax-check the JS.** Re-extract just the Component script (or
re-run `extract_bundle.py`, which refreshes `component.js` too) and run:

```bash
node --check /tmp/work/component.js
```

This catches a mismatched brace, an unclosed string, a stray comma — the
things a bundler's compiler would normally catch for you.

**b. Tag-balance the HTML.** The markup has no real parser involved until
the browser renders it, so an unclosed `<sc-if>` or an extra `</div>`
fails silently until runtime, often nowhere near where you edited.

```bash
python3 scripts/check_tag_balance.py /tmp/work/template.html
```

If your edit added/removed any tags, the open/close counts should move by
the exact number of tags you added or removed — if a count mismatches,
you have a markup bug to find before going further.

## 5. Repack

```bash
python3 scripts/repack_bundle.py vercel-standalone/index.html /tmp/work/template.html /tmp/work/roundtrip.html
```

This re-encodes `template.html` back into the bundle's JSON-string format.

## 6. Diff-verify — the step that's easy to skip and shouldn't be

The repacked file is still one giant JSON-escaped line, so a normal `diff`
is useless for eyeballing it. Before trusting the repack, prove the change
is **exactly** what you intended and nothing else, two ways:

**For a single, well-isolated edit** — find the common prefix and common
suffix between the original and the repacked file (as plain byte strings)
and inspect only what's different in the middle:

```python
orig = open("vercel-standalone/index.html", encoding="utf-8").read()
new  = open("/tmp/work/roundtrip.html", encoding="utf-8").read()
i = 0
while i < min(len(orig), len(new)) and orig[i] == new[i]:
    i += 1
j = 0
while j < min(len(orig), len(new)) - i and orig[-1-j] == new[-1-j]:
    j += 1
print("ORIG MIDDLE:", repr(orig[i:len(orig)-j]))
print("NEW  MIDDLE:", repr(new[i:len(new)-j]))
```

If the "middle" on both sides is exactly your intended before/after text
(allowing for `\n` → `\\n` and `"` → `\"` JSON-escaping), you're clear.

**For multiple edits scattered across the file**, re-extract BOTH the
pre-edit original and your edited `template.html` into plain multi-line
text, and run a normal line-based `diff -u` between them — this works
because, unlike the packed bundle, the extracted template is real
multi-line HTML again:

```bash
python3 scripts/extract_bundle.py vercel-standalone/index.html /tmp/orig
diff -u /tmp/orig/template.html /tmp/work/template.html
```

Read every hunk. If anything appears that you didn't intend to touch,
stop and find out why before shipping — on a file this size, an
unintended match in an `old_string` silently changing a second,
coincidentally-identical occurrence elsewhere is a real failure mode.

## 7. Copy, commit, push

```bash
cp /tmp/work/roundtrip.html vercel-standalone/index.html
git add vercel-standalone/index.html
git commit -m "<type>: <what changed, in one line>

<why, if it's not obvious from the summary — especially for bug fixes,
state the root cause you found, not just the symptom you patched>"
git push -u origin claude/<short-description>
```

## 8. Open a PR against the production branch — never push straight to it

Write the PR body to answer three things a reviewer (or future you) would
ask: what changed, why (root cause for bugs), how to verify it. Keep the
diff scoped to the one request — resist folding in an unrelated
improvement you noticed along the way; that's a separate branch and PR.

## 9. Wait for explicit confirmation before merging

Even when you're confident the change is correct, don't merge
automatically. Validated code can still be the wrong call, have a UX
tradeoff the user wants to weigh in on, or simply be something they want
to see live first. Ship the PR, summarize what it does and how you
verified it, and wait to be told to merge.

## 10. If two PRs land out of order

Merging PR A after PR B was already merged means B's branch is now stale
— since the whole file is one JSON blob, two independent edits to
*different* parts of it will still produce a git merge **conflict** on
the single line, even though the changes don't logically overlap (git
diffs by line, and there's only one line). Don't try to hand-resolve that
conflict inside the escaped JSON. Instead: reset the stale branch onto the
new tip of the production branch, re-extract fresh, redo the edit (it's
usually a small, mechanical reapplication of the same patch), revalidate,
repack, diff-verify again, and force-push. Treat it exactly like a fresh
instance of this loop, not a merge to untangle.

## When a bug is in the *data*, not the code

If the user reports something that turns out to be bad data already
sitting in Supabase (a typo'd category that split into two, a stale
status value), that's not this loop — see `references/database.md`'s
"Data fixes" section. Fix the data directly via `execute_sql`, AND fix the
code path that let the bad value get written in the first place, so it
doesn't recur. Shipping only one of those two fixes leaves either live
data still wrong, or the root cause still open to reproduce the bug.
