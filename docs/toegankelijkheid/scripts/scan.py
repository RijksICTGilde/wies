import json

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
PAGES = [
    ("/", "Wie zit waar? (overzicht)"),
    ("/opdrachten/", "Opdrachten"),
    ("/beheer/gebruikers/", "Beheer - gebruikers"),
    ("/beheer/labels/", "Beheer - labels"),
    ("/beheer/merken/", "Beheer - merken"),
    ("/beheer/organisaties/", "Beheer - organisaties"),
    ("/faq/", "Veelgestelde vragen"),
    ("/contact/", "Contact"),
    ("/privacy/", "Privacy"),
    ("/toegankelijkheid/", "Toegankelijkheid"),
    ("/profiel/", "Profiel"),
]

AXE = open("axe.min.js").read()
# WCAG 2.1 A + AA only: the statement is scoped to those.
OPTS = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}}

results = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    for path, label in PAGES:
        try:
            r = pg.goto(BASE + path, wait_until="networkidle", timeout=20000)
            pg.wait_for_timeout(1200)
            status = r.status if r else 0
            pg.evaluate(AXE)
            out = pg.evaluate("async (o) => await axe.run(document, o)", OPTS)
            results.append(
                {
                    "path": path,
                    "label": label,
                    "status": status,
                    "violations": out["violations"],
                    "passes": len(out["passes"]),
                    "incomplete": [i["id"] for i in out["incomplete"]],
                }
            )
            n = sum(len(v["nodes"]) for v in out["violations"])
            print(f"{status} {path:34} violations={len(out['violations']):2} nodes={n:3} passes={len(out['passes'])}")
        except Exception as e:
            print(f"ERR {path}: {str(e)[:80]}")
            results.append({"path": path, "label": label, "error": str(e)[:200]})
    b.close()

json.dump(results, open("scan.json", "w"), indent=1)
print("\n-> scan.json")
