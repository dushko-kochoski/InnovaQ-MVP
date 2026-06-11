"""Validates translations.js against the HTML pages.

1. en/mk key sets must be identical.
2. Every non-js.* en value (normalized like the runtime does) must appear in
   at least one HTML page — otherwise the runtime will never annotate it and
   the string silently stays English.
"""

import json
import re
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def normalize(text: str) -> str:
    text = re.sub(r"<[^>]*>", " ", text)
    text = text.replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def load_dicts() -> tuple[dict, dict]:
    source = (FRONTEND / "translations.js").read_text(encoding="utf-8")
    dicts: dict[str, dict] = {}
    current = None
    pattern = re.compile(r'^\s+"((?:[^"\\]|\\.)+)":\s+"((?:[^"\\]|\\.)*)",?\s*$')
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("en: {"):
            current = dicts.setdefault("en", {})
            continue
        if stripped.startswith("mk: {"):
            current = dicts.setdefault("mk", {})
            continue
        if current is None:
            continue
        match = pattern.match(line)
        if match:
            key = json.loads(f'"{match.group(1)}"')
            value = json.loads(f'"{match.group(2)}"')
            current[key] = value
    return dicts["en"], dicts["mk"]


def main() -> int:
    en, mk = load_dicts()
    failures = 0

    only_en = set(en) - set(mk)
    only_mk = set(mk) - set(en)
    if only_en or only_mk:
        failures += 1
        print(f"KEY PARITY: only in en={sorted(only_en)} only in mk={sorted(only_mk)}")

    raw_pages = {p: p.read_text(encoding="utf-8") for p in sorted(FRONTEND.rglob("*.html"))}
    pages = {p: normalize(content) for p, content in raw_pages.items()}

    unmatched = []
    for key, value in en.items():
        if key.startswith("js."):
            continue
        needle = normalize(value)
        if any(needle in content for content in pages.values()):
            continue
        # placeholders live in attributes (stripped by normalize); runtime
        # matches them against el.placeholder, so check the raw HTML
        placeholder = f'placeholder="{value}"'
        if any(placeholder in raw for raw in raw_pages.values()):
            continue
        unmatched.append((key, needle[:90]))
    if unmatched:
        failures += 1
        print(f"{len(unmatched)} en values match no page text:")
        for key, preview in unmatched:
            print(f"  {key}: {preview}")

    static_keys = sum(1 for k in en if not k.startswith("js."))
    print(f"\nkeys: {len(en)} total, {static_keys} static, {len(en) - static_keys} js-only")
    print(f"pages scanned: {len(pages)}")
    print("RESULT:", "FAIL" if failures else "PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
