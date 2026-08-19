"""Toegankelijke naam via de ECHTE accessibility tree, niet via een eigen gok."""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
    for path in ["/", "/beheer/gebruikers/"]:
        pg.goto("http://localhost:8080" + path, wait_until="networkidle")
        pg.wait_for_timeout(1200)
        snap = pg.accessibility.snapshot(interesting_only=True)
        naamloos = []
        totaal = 0

        def walk(n):
            global totaal
            if not n:
                return
            role = n.get("role", "")
            name = (n.get("name") or "").strip()
            if role in ("button", "link", "checkbox", "textbox", "combobox", "menuitem", "tab", "switch"):
                totaal += 1
                if not name:
                    naamloos.append(role)
            for c in n.get("children", []) or []:
                walk(c)

        walk(snap)
        from collections import Counter

        print(
            f"{path:22} interactieve elementen in a11y-tree: {totaal:3} | zonder naam: {len(naamloos)} {dict(Counter(naamloos))}"
        )
    b.close()
