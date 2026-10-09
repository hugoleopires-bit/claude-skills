#!/usr/bin/env python3
"""
Re-encodes an edited template.html back into the single-file bundle
format. Also doubles as a self-test: run it with the UNedited
template.html and it should produce a byte-identical copy of the
original — that proves the encode/decode roundtrip itself is sound,
before you ever trust it with a real edit.

Usage:
    python3 repack_bundle.py <original index.html> <edited template.html> <output index.html>

The manifest is copied through unchanged (this script only ever
touches the template string) — if your edit also needs new manifest
blobs (e.g. a new embedded asset), handle that separately.
"""
import re, json, sys


def encode_template(s):
    # Must match exactly how the platform encodes it: json.dumps with
    # ensure_ascii=False (keep UTF-8 literal, don't \uXXXX-escape it),
    # then escape "</" so a literal </script> inside the HTML can't
    # prematurely close the wrapping <script> tag.
    return json.dumps(s, ensure_ascii=False).replace('</', '<\\/')


def encode_manifest(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def repack(src, template_file, out_file):
    raw = open(src, "r", encoding="utf-8").read()
    m_manifest = re.search(r'(<script type="__bundler/manifest">)(.*?)(</script>)', raw, re.S)
    m_template = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', raw, re.S)

    manifest_obj = json.loads(m_manifest.group(2))
    new_template_str = open(template_file, "r", encoding="utf-8").read()

    new_manifest_text = encode_manifest(manifest_obj)
    new_template_text = encode_template(new_template_str)

    out = raw[:m_manifest.start(2)] + new_manifest_text + raw[m_manifest.end(2):]
    # Recompute the template match on `out`, since the manifest replacement
    # above may have shifted every offset after it.
    m_template2 = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', out, re.S)
    out = out[:m_template2.start(2)] + new_template_text + out[m_template2.end(2):]

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: repack_bundle.py <original index.html> <edited template.html> <output index.html>")
        sys.exit(1)
    src, template_file, out_file = sys.argv[1], sys.argv[2], sys.argv[3]
    out = repack(src, template_file, out_file)
    orig = open(src, "r", encoding="utf-8").read()
    if out == orig:
        print("byte-identical round trip (template.html had no edits).")
    else:
        print("repacked with edits — len orig", len(orig), "len out", len(out))
        print("Now diff <out_file> against <src> (e.g. via extract_bundle.py on both and a")
        print("plain-text diff) and confirm the only change is the one you intended.")
