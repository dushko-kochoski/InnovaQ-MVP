"""One-shot: wire translations.js + МК/EN toggle into every frontend page. Idempotent."""

from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

TAILWIND = '<script src="https://cdn.tailwindcss.com"></script>'
I18N_INCLUDE = '<script src="/translations.js"></script>'

NAV_ANCHOR = (
    '<a href="/app/dashboard.html" class="bg-indigo-600 hover:bg-indigo-700 '
    'text-white text-sm font-semibold px-4 py-2 rounded-lg transition">Open Dashboard</a>'
)

TOGGLE = """<div class="flex items-center text-sm font-medium">
        <button data-lang-btn="mk" onclick="setLanguage('mk')" class="px-1.5 py-0.5 text-slate-500 hover:text-indigo-600">МК</button>
        <span class="text-slate-300">/</span>
        <button data-lang-btn="en" onclick="setLanguage('en')" class="px-1.5 py-0.5 text-slate-500 hover:text-indigo-600">EN</button>
      </div>
      """


def main() -> None:
    for path in sorted(FRONTEND.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        changed = []
        if I18N_INCLUDE not in text:
            if TAILWIND not in text:
                print(f"SKIP {path.name}: no tailwind include found")
                continue
            text = text.replace(TAILWIND, TAILWIND + "\n  " + I18N_INCLUDE, 1)
            changed.append("script")
        if "data-lang-btn" not in text:
            if NAV_ANCHOR not in text:
                print(f"WARN {path.name}: nav anchor not found, toggle not added")
            else:
                text = text.replace(NAV_ANCHOR, TOGGLE + NAV_ANCHOR, 1)
                changed.append("toggle")
        if changed:
            path.write_text(text, encoding="utf-8", newline="\n")
        rel = path.relative_to(FRONTEND)
        print(f"OK   {rel}: {'+'.join(changed) if changed else 'already wired'}")


if __name__ == "__main__":
    main()
