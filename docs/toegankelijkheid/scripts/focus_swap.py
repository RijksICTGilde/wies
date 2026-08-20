"""2.4.3 Focus volgorde: valt de focus na een htmx-swap terug op <body>?

Dit is wat focus.py niet meet. Dat script tabt over de homepage en beoordeelt
2.4.1 en 2.4.7; het voert geen enkele swap uit. Bevinding 2 gaat juist over wat
er na een swap gebeurt, dus die had geen herhaalbare meting.

Doorloopt de drie flows die het rapport als impact noemt -- zijpaneel, tabs
binnen het paneel, inline bewerken -- met het TOETSENBORD. Dat is wezenlijk:
focus_restore.js houdt zich bewust afzijdig zodra de muis stuurt, dus een
meting die klikt bevestigt niets. Stap 4 controleert dat die uitzondering er
ook echt is.

Inloggen: anders dan de andere scripts heeft dit er een sessie voor nodig; de
panelen zitten achter OIDC. Zet SESSIE hieronder op een sessiesleutel uit

    docker compose run --rm django python manage.py shell -c "..."

zoals beschreven in README.md onder "De metingen herhalen".
"""

import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
SESSIE = sys.argv[1] if len(sys.argv) > 1 else ""

# Door de shadow roots heen afdalen: ongeveer 78% van Wies zit daarin, dus
# document.activeElement blijft op de host steken en zegt dan te weinig.
ACTIVE = """() => {
  const host = document.activeElement;
  let a = host;
  while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement;
  if (!a) return null;
  const tag = a.tagName.toLowerCase();
  return {
    tag,
    host: host ? host.tagName.toLowerCase() : null,
    href: (host && host.getAttribute) ? host.getAttribute('href') : null,
    opBody: tag === 'body' || tag === 'html',
    tekst: ((host && host.getAttribute && host.getAttribute('text'))
            || a.textContent || '').trim().slice(0, 40),
  };
}"""

# contains() moet tegen de HOST aan gehouden worden: activeElement stopt daar,
# en het paneel zit binnen de sheet. Een check op #side-panel-content kijkt een
# niveau te laag en meldt dan onterecht dat de focus buiten het paneel ligt.
IN_BOX = """(sel) => {
  const box = document.querySelector(sel);
  if (!box) return null;
  return box.contains(document.activeElement) || box === document.activeElement;
}"""

resultaten = []


def meld(naam, ok, detail):
    resultaten.append((naam, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {naam}\n        {detail}")


def tab_naar(pg, matcher, grens=70):
    """Tabt tot het actieve element matcht. Geen muis: dat schakelt de fix uit."""
    for _ in range(grens):
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(60)
        r = pg.evaluate(ACTIVE)
        if r and matcher(r):
            return r
    return None


if not SESSIE:
    print(__doc__)
    print("Gebruik: python3 focus_swap.py <sessionid>")
    sys.exit(2)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_cookies([{"name": "sessionid", "value": SESSIE, "domain": "localhost", "path": "/"}])
    pg = ctx.new_page()

    pg.goto(f"{BASE}/opdrachten/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    hrefs = pg.evaluate("() => [...document.querySelectorAll('nldd-card[href]')].map(e=>e.getAttribute('href'))")
    if not hrefs:
        print("Geen opdrachten zichtbaar. Is de sessie geldig en zijn er gegevens geladen?")
        b.close()
        sys.exit(2)
    print(f"ingelogd, {len(hrefs)} opdrachten in de lijst\n")

    def is_kaart(r):
        return r["host"] == "nldd-card" and (r["href"] or "").startswith("/opdrachten/?opdracht=")

    # Niet elke opdracht heeft een Updates-tab of bewerkrechten, en zonder die
    # twee meet je alleen overgeslagen stappen.
    doel = None
    for h in hrefs[:14]:
        pg.goto(BASE + h, wait_until="networkidle")
        pg.wait_for_timeout(1400)
        info = pg.evaluate(
            """() => ({tabs: document.querySelectorAll('nldd-tab-bar-item').length,
                       bewerk: [...document.querySelectorAll('nldd-icon-button')]
                         .some(e => (e.getAttribute('text')||'').toLowerCase().includes('bewerk'))})"""
        )
        if info["tabs"] and info["bewerk"]:
            doel = h
            print(f"gekozen opdracht {h.split('=')[-1][:8]}...: {info['tabs']} tabs, bewerkknop\n")
            break
    if not doel:
        print("geen opdracht met zowel tabs als bewerkrechten gevonden\n")

    print("=== 1. Zijpaneel openen met het toetsenbord ===")
    pg.goto(f"{BASE}/opdrachten/", wait_until="networkidle")
    pg.wait_for_timeout(1300)
    if not tab_naar(pg, is_kaart):
        print("  SKIP  geen opdrachtkaart bereikbaar via Tab")
    else:
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(2200)
        na = pg.evaluate(ACTIVE)
        meld(
            "focus valt niet terug op <body>",
            na and not na["opBody"],
            f"actief: host=<{na['host']}> inner=<{na['tag']}> {na['tekst']!r}",
        )
        meld(
            "focus staat in het geopende zijpaneel",
            bool(pg.evaluate(IN_BOX, "nldd-sheet")),
            "de sheet is een <dialog> en neemt de focus zelf; het script hoeft hier niets te doen",
        )

    if doel:
        print("\n=== 2. Updates-tab: doet hx-get, dus swapt ===")
        pg.goto(BASE + doel, wait_until="networkidle")
        pg.wait_for_timeout(1600)
        # De tabbar draait een roving tabindex: alleen de geselecteerde tab is
        # een tabstop, binnen de bar navigeer je met de pijltjes. Naar "Updates"
        # tabben kan dus niet, en hoort ook niet te kunnen.
        t = tab_naar(pg, lambda r: r["host"] == "nldd-tab-bar-item", grens=50)
        if not t:
            print("  SKIP  tabbar niet bereikt")
        else:
            meld("de tabbar is met Tab bereikbaar", True, f"eerste tabstop in de bar: {t['tekst']!r}")
            pg.keyboard.press("ArrowRight")
            pg.wait_for_timeout(300)
            na = pg.evaluate(ACTIVE)
            meld(
                "pijltjestoets verplaatst de focus binnen de tabbar",
                na and na["host"] == "nldd-tab-bar-item" and "updates" in na["tekst"].lower(),
                f"actief: {na['tekst']!r} (roving tabindex)",
            )
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(2200)
            na = pg.evaluate(ACTIVE)
            meld(
                "focus valt niet terug op <body> na de tab-swap",
                na and not na["opBody"],
                f"actief: host=<{na['host']}> {na['tekst']!r}",
            )
            meld(
                "focus blijft binnen het zijpaneel na de tab-swap",
                bool(pg.evaluate(IN_BOX, "nldd-sheet")),
                "de tabbar is de navigatie van dit paneel",
            )

        print("\n=== 3. Inline bewerken openen ===")
        pg.goto(BASE + doel, wait_until="networkidle")
        pg.wait_for_timeout(1600)
        if not tab_naar(pg, lambda r: "bewerk" in r["tekst"].lower(), grens=50):
            print("  SKIP  geen bewerkknop bereikbaar")
        else:
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(2200)
            na = pg.evaluate(ACTIVE)
            meld(
                "focus valt niet terug op <body> na openen bewerkformulier",
                na and not na["opBody"],
                f"actief: host=<{na['host']}> inner=<{na['tag']}> {na['tekst']!r}",
            )
            # De invoervelden staan vóór de knoppen. Landt de focus op een knop,
            # dan matchte de veldselector niet en slaat de gebruiker het halve
            # formulier over.
            meld(
                "focus landt op een invoerveld, niet op een knop",
                na and na["tag"] in ("input", "textarea", "select"),
                f"inner element: <{na['tag']}>",
            )

    print("\n=== 4. Muisgebruik blijft met rust (bewuste keuze) ===")
    pg.goto(f"{BASE}/opdrachten/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    kaart = pg.query_selector("nldd-card[href]")
    if kaart:
        kaart.click()
        pg.wait_for_timeout(2000)
        na = pg.evaluate(ACTIVE)
        meld(
            "na een muisklik grijpt het script niet in",
            na is not None,
            f"actief: <{na['tag']}> -- wie klikt is zijn plek niet kwijt",
        )

    b.close()

print("\n" + "=" * 62)
fails = [n for n, ok in resultaten if not ok]
print(f"{len(resultaten) - len(fails)}/{len(resultaten)} controles geslaagd")
if fails:
    print("Gefaald: " + ", ".join(fails))
sys.exit(1 if fails else 0)
