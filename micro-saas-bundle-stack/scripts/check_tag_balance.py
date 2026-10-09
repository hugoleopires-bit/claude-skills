#!/usr/bin/env python3
"""
Sanity-checks that tags are balanced in an edited template.html.

Why this matters: the bundle's markup is plain stringified HTML with
no real parser anywhere in this loop — the browser is the first thing
that will ever actually parse it. An unclosed <sc-if> or a stray extra
</div> silently breaks the page at runtime, often far from where you
edited, and the failure mode is a blank screen or garbled layout with
no stack trace pointing at the cause. This catches that class of
mistake before you ship, by counting open vs. close tags.

It's a heuristic (regex counting), not a real parser — it won't catch
a WRONGLY NESTED-but-balanced-in-count pair. Pair it with an actual
diff review of your edit for anything structurally risky.

Usage:
    python3 check_tag_balance.py <template.html> [tag1 tag2 ...]
Defaults to checking: sc-if sc-for sc-raw-select div label textarea
(add any other custom/void-exempt tags your templating syntax uses).
"""
import re, sys

DEFAULT_TAGS = ["sc-if", "sc-for", "sc-raw-select", "div", "label", "textarea"]


def main():
    if len(sys.argv) < 2:
        print("usage: check_tag_balance.py <template.html> [tag1 tag2 ...]")
        sys.exit(1)
    path = sys.argv[1]
    tags = sys.argv[2:] or DEFAULT_TAGS
    html = open(path, encoding="utf-8").read()
    ok = True
    for tag in tags:
        opens = len(re.findall(rf'<{tag}(?:\s[^>]*)?>', html))
        closes = len(re.findall(rf'</{tag}>', html))
        status = "OK" if opens == closes else "MISMATCH"
        if opens != closes:
            ok = False
        print(f"{tag:15s} open={opens:4d} close={closes:4d} {status}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
