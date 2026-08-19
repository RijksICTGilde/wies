"""4.1.1 Parsen: dubbele id's en verkeerd genest HTML."""

from playwright.sync_api import sync_playwright

PAGES = [
    "/",
    "/opdrachten/",
    "/beheer/gebruikers/",
    "/faq/",
    "/profiel/",
    "/contact/",
    "/privacy/",
    "/toegankelijkheid/",
    "/beheer/labels/",
    "/beheer/merken/",
    "/beheer/organisaties/",
]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
    tot_dup = 0
    for path in PAGES:
        pg.goto("http://localhost:8080" + path, wait_until="networkidle")
        pg.wait_for_timeout(800)
        r = pg.evaluate("""() => {
          const ids={}; const dup=[];
          const walk=(root)=>{ root.querySelectorAll('[id]').forEach(el=>{
              const k=el.id; ids[k]=(ids[k]||0)+1; if(ids[k]===2) dup.push(k); });
          };
          walk(document);   // alleen light DOM: id's zijn per shadow root uniek
          return {dup, totaalIds:Object.keys(ids).length};
        }""")
        tot_dup += len(r["dup"])
        if r["dup"]:
            print(f"  {path:26} dubbele id's: {r['dup'][:5]}")
    print("totaal dubbele id's over 11 pagina's:", tot_dup)
    b.close()
