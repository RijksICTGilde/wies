"""De nieuwe WCAG 2.2-criteria: 2.4.11, 3.2.6, 3.3.7, 3.3.8 (+ 2.5.7 opnieuw)."""

import json

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
PAGES = [
    "/",
    "/opdrachten/",
    "/beheer/gebruikers/",
    "/beheer/labels/",
    "/beheer/merken/",
    "/beheer/organisaties/",
    "/profiel/",
    "/faq/",
    "/contact/",
    "/privacy/",
    "/toegankelijkheid/",
]
res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()

    # --- 3.2.6 Consistente hulp: staat een hulp-/contactmogelijkheid op elke pagina,
    #     steeds op dezelfde relatieve plek?
    hulp = []
    for path in PAGES:
        pg.goto(BASE + path, wait_until="networkidle")
        pg.wait_for_timeout(800)
        hulp.append(
            pg.evaluate(
                """(p) => {
          const links=[...document.querySelectorAll('a[href]')];
          const contact=links.filter(a=>/contact|hulp|help|veelgestelde|faq/i.test(a.textContent+a.getAttribute('href')));
          // positie: staat het in de footer?
          const inFooter=contact.filter(a=>a.closest('nldd-page-footer,footer'));
          return {page:p, aantal:contact.length, inFooter:inFooter.length,
                  teksten:contact.map(a=>a.textContent.trim()).slice(0,4)};
        }""",
                path,
            )
        )
    res["consistente_hulp"] = hulp

    # --- 3.3.7 Overbodige invoer: wordt eerder ingevoerde info opnieuw gevraagd?
    #     Indicatie: formuliervelden die al een waarde hebben bij bewerken.
    pg.goto(BASE + "/beheer/gebruikers/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    res["overbodige_invoer"] = pg.evaluate("""() => {
      const out={velden:0, voorgevuld:0, autocomplete:0};
      const walk=(r)=>{ r.querySelectorAll('input,textarea,select').forEach(el=>{
          if(['hidden','submit','button'].includes(el.type)) return;
          out.velden++;
          if(el.value && el.value.trim()) out.voorgevuld++;
          if(el.autocomplete && el.autocomplete!=='off') out.autocomplete++; });
        r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
      walk(document); return out; }""")

    # --- 3.3.8 Toegankelijke authenticatie: is er een cognitieve test bij inloggen?
    res["authenticatie"] = {
        "methode": "OIDC via Keycloak (externe leverancier)",
        "captcha_in_app": pg.evaluate(
            """() => document.querySelectorAll('[class*=captcha],[id*=captcha],iframe[src*=recaptcha]').length"""
        ),
        "wachtwoordveld_in_app": pg.evaluate("""() => document.querySelectorAll('input[type=password]').length"""),
    }

    # --- 2.4.11 Focus niet bedekt: wordt het element met focus verborgen door
    #     vaste elementen (sticky header/footer)?
    pg.goto(BASE + "/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    sticky = pg.evaluate("""() => {
      const out=[]; const walk=(r)=>{ r.querySelectorAll('*').forEach(el=>{
          const cs=getComputedStyle(el);
          if(cs.position==='fixed'||cs.position==='sticky'){
            const b=el.getBoundingClientRect();
            if(b.height>0&&b.width>0) out.push({tag:el.tagName.toLowerCase(), pos:cs.position,
              top:Math.round(b.top), h:Math.round(b.height), z:cs.zIndex}); }
          if(el.shadowRoot) walk(el.shadowRoot); }); };
      walk(document); return out.slice(0,10); }""")
    # tab door de pagina en kijk of het gefocuste element in beeld blijft
    bedekt = []
    for i in range(16):
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(90)
        r = pg.evaluate("""() => { let a=document.activeElement;
          while(a&&a.shadowRoot&&a.shadowRoot.activeElement) a=a.shadowRoot.activeElement;
          if(!a||!a.getBoundingClientRect) return null;
          const b=a.getBoundingClientRect();
          if(b.width===0||b.height===0) return null;
          // welk element ligt op het middelpunt van het gefocuste element?
          const cx=b.left+b.width/2, cy=b.top+b.height/2;
          if(cy<0||cy>innerHeight) return {buitenBeeld:true, tag:a.tagName.toLowerCase()};
          const top=document.elementFromPoint(cx,cy);
          const bedekt = top && top!==a && !a.contains(top) && !(top.contains&&top.contains(a));
          return {buitenBeeld:false, bedekt:!!bedekt, tag:a.tagName.toLowerCase(),
                  dekker: bedekt&&top?top.tagName.toLowerCase():null}; }""")
        if r and (r.get("buitenBeeld") or r.get("bedekt")):
            bedekt.append(r)
    res["focus_niet_bedekt"] = {"sticky_elementen": sticky, "problemen": bedekt}
    b.close()
json.dump(res, open("wcag22.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:1500])
