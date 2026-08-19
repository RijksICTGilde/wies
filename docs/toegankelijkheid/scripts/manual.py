"""Criteria a scanner cannot decide: keyboard, focus, structure, language, reflow."""

import json

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
PAGES = ["/", "/opdrachten/", "/beheer/gebruikers/", "/faq/", "/profiel/"]
res = {}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()

    # --- 3.1.1 Taal van de pagina (A) + 2.4.2 Paginatitel (A) + 1.3.1 koppen
    lang = []
    for path in PAGES:
        pg.goto(BASE + path, wait_until="networkidle")
        pg.wait_for_timeout(900)
        lang.append(
            pg.evaluate(
                """(p) => {
          const hs=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h=>+h.tagName[1]);
          let jumps=[]; for(let i=1;i<hs.length;i++) if(hs[i]-hs[i-1]>1) jumps.push(hs[i-1]+'->'+hs[i]);
          return {page:p, lang:document.documentElement.lang||null, title:document.title||null,
                  h1:document.querySelectorAll('h1').length, koppen:hs.length, sprongen:jumps,
                  main:document.querySelectorAll('main,[role=main],nldd-page').length,
                  landmarks:{nav:document.querySelectorAll('nav,[role=navigation]').length,
                             header:document.querySelectorAll('header,[role=banner]').length,
                             footer:document.querySelectorAll('footer,[role=contentinfo]').length}};
        }""",
                path,
            )
        )
    res["structuur"] = lang

    # --- 2.4.1 Blokken omzeilen (A): skip-link?
    pg.goto(BASE + "/", wait_until="networkidle")
    pg.wait_for_timeout(900)
    pg.keyboard.press("Tab")
    res["skiplink"] = pg.evaluate("""() => {
      const deep=(d)=>{ let a=d.activeElement; while(a&&a.shadowRoot&&a.shadowRoot.activeElement) a=a.shadowRoot.activeElement; return a; };
      const el=deep(document);
      return {eerste_tabstop: el?el.tagName.toLowerCase():null,
              tekst:(el?.textContent||el?.getAttribute?.('text')||'').trim().slice(0,50),
              is_skiplink: /skip|spring|naar inhoud/i.test((el?.textContent||'')+(el?.getAttribute?.('text')||''))};
    }""")

    # --- 2.1.1 Toetsenbord (A): hoeveel stops tot de eerste inhoud
    stops = []
    for i in range(14):
        pg.keyboard.press("Tab")
        stops.append(
            pg.evaluate("""() => { const deep=(d)=>{let a=d.activeElement;
          while(a&&a.shadowRoot&&a.shadowRoot.activeElement) a=a.shadowRoot.activeElement; return a;};
          const el=deep(document); if(!el) return null;
          return (el.tagName.toLowerCase()+': '+((el.getAttribute&&(el.getAttribute('text')||el.getAttribute('aria-label')))||el.textContent||'').trim().slice(0,32)); }""")
        )
    res["tabvolgorde_home"] = stops

    # --- 2.4.7 Focus zichtbaar (AA)
    res["focus_zichtbaar"] = pg.evaluate("""() => {
      const deep=(d)=>{let a=d.activeElement; while(a&&a.shadowRoot&&a.shadowRoot.activeElement) a=a.shadowRoot.activeElement; return a;};
      const el=deep(document); if(!el) return null;
      const cs=getComputedStyle(el);
      return {outline:cs.outlineStyle+' '+cs.outlineWidth, boxShadow:cs.boxShadow.slice(0,40)};
    }""")

    # --- 1.4.4 Tekst schalen 200% (AA) + 1.4.10 Reflow (AA, 320px)
    pg.goto(BASE + "/", wait_until="networkidle")
    pg.wait_for_timeout(800)
    zoom = []
    for w, label in [(1440, "100%"), (720, "200% (equivalent)"), (320, "reflow 320px")]:
        pg.set_viewport_size({"width": w, "height": 900})
        pg.wait_for_timeout(800)
        zoom.append(
            pg.evaluate(
                """(l) => ({staat:l, horizontaal_scrollen: document.documentElement.scrollWidth > document.documentElement.clientWidth+1,
                 scrollWidth:document.documentElement.scrollWidth, clientWidth:document.documentElement.clientWidth})""",
                label,
            )
        )
    res["reflow"] = zoom

    # --- 1.1.1 Niet-tekstuele content (A): afbeeldingen zonder alt
    pg.set_viewport_size({"width": 1440, "height": 900})
    imgs = []
    for path in PAGES:
        pg.goto(BASE + path, wait_until="networkidle")
        pg.wait_for_timeout(800)
        imgs.append(
            pg.evaluate(
                """(p) => { const out=[]; const walk=(r)=>{ r.querySelectorAll('img,svg').forEach(el=>{
            if(el.shadowRoot) walk(el.shadowRoot);
            if(el.tagName==='IMG' && !el.hasAttribute('alt')) out.push('img zonder alt: '+el.src.slice(-40));
            if(el.tagName==='svg' && !el.getAttribute('aria-hidden') && !el.getAttribute('aria-label') && !el.querySelector('title')) out.push('svg zonder naam/aria-hidden'); });
            r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
          walk(document); return {page:p, problemen: [...new Set(out)].slice(0,5), totaal: out.length}; }""",
                path,
            )
        )
    res["afbeeldingen"] = imgs
    b.close()

json.dump(res, open("manual.json", "w"), indent=1, ensure_ascii=False)
for k, v in res.items():
    print(f"\n=== {k}")
    print(json.dumps(v, indent=1, ensure_ascii=False)[:900])
