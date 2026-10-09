#!/usr/bin/env python3
"""
Extracts the editable pieces out of a single-file HTML bundle (the
"Claude Design bundle" format: a <script type="__bundler/manifest">
+ a <script type="__bundler/template"> + an inline Component script)
into plain files you can diff and edit with normal tools.

Why this exists: the bundle's markup lives as a JSON-encoded string
inside <script type="__bundler/template">, so you can't just open the
file and edit the HTML directly — any editor will show you one giant
escaped line. This decodes it into real, multi-line HTML.

Usage:
    python3 extract_bundle.py <path/to/index.html> <output_dir>

Produces in <output_dir>:
    template.html   - the full page markup, decoded and editable
    component.js    - just the inline Component class script, for syntax-checking
    runtime.js      - the bundled runtime script, if the manifest has one (rarely edited)
"""
import re, json, base64, gzip, sys, os


def main():
    if len(sys.argv) != 3:
        print("usage: extract_bundle.py <index.html> <output_dir>")
        sys.exit(1)
    src, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    raw = open(src, "r", encoding="utf-8").read()

    m_manifest = re.search(r'<script type="__bundler/manifest">(.*?)</script>', raw, re.S)
    m_template = re.search(r'<script type="__bundler/template">(.*?)</script>', raw, re.S)
    if not m_manifest or not m_template:
        print("Could not find __bundler/manifest or __bundler/template scripts — is this a bundle file?")
        sys.exit(1)

    manifest = json.loads(m_manifest.group(1))
    template_html = json.loads(m_template.group(1))

    with open(os.path.join(out_dir, "template.html"), "w", encoding="utf-8") as f:
        f.write(template_html)

    # Follow a <script src="UUID"> reference into the manifest blobs — that's
    # the bundled runtime, base64-encoded and sometimes gzip-compressed.
    m_rt = re.search(r'<script src="([0-9a-fA-F-]{36})"', template_html)
    runtime_found = False
    if m_rt:
        blob = manifest.get(m_rt.group(1))
        if blob:
            data = base64.b64decode(blob["data"])
            if blob.get("compressed"):
                data = gzip.decompress(data)
            with open(os.path.join(out_dir, "runtime.js"), "w", encoding="utf-8") as f:
                f.write(data.decode("utf-8"))
            runtime_found = True

    m_dc = re.search(r'<script[^>]*data-dc-script[^>]*>(.*?)</script>', template_html, re.S)
    if m_dc:
        with open(os.path.join(out_dir, "component.js"), "w", encoding="utf-8") as f:
            f.write(m_dc.group(1))

    print("manifest blobs:", len(manifest))
    print("template_html length:", len(template_html))
    print("runtime found:", runtime_found)
    print("component found:", m_dc is not None, len(m_dc.group(1)) if m_dc else 0)


if __name__ == "__main__":
    main()
