"""Aanvullende metingen voor de criteria die het rapport expliciet moet noemen."""

import json

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
PAGES = ["/", "/opdrachten/", "/beheer/gebruikers/", "/faq/", "/profiel/", "/contact/"]
res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()

    # 3.1.2 Taal van onderdelen / 2.4.4 Linkdoel / 2.5.3 Label in naam / 4.1.2 naam-rol-waarde
    out = []
    for path in PAGES:
        pg.goto(BASE + path, wait_until="networkidle")
        pg.wait_for_timeout(900)
        out.append(
            pg.evaluate(
                """(p) => {
          const A=[...document.querySelectorAll('a[href]')];
          const vagelinks=A.filter(a=>/^(lees meer|meer|klik hier|hier|link)$/i.test(a.textContent.trim())).map(a=>a.textContent.trim());
          // 2.5.3: zichtbare tekst moet in de toegankelijke naam zitten
          const mismatch=[];
          [...document.querySelectorAll('[aria-label]')].forEach(el=>{
            const vis=(el.textContent||'').trim(); const al=el.getAttribute('aria-label')||'';
            if(vis && al && !al.toLowerCase().includes(vis.toLowerCase().slice(0,12))) mismatch.push(vis.slice(0,24)+' | aria-label='+al.slice(0,24));
          });
          // 4.1.2: knoppen/links zonder toegankelijke naam
          const naamloos=[];
          const walk=(r)=>{ r.querySelectorAll('button,a[href],[role=button]').forEach(el=>{
              const n=(el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent||'').trim();
              if(!n) naamloos.push(el.tagName.toLowerCase()+(el.className?('.'+String(el.className).slice(0,18)):''));
            });
            r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
          walk(document);
          return {page:p, links:A.length, vagelinks, labelMismatch:mismatch.slice(0,4),
                  naamloos:[...new Set(naamloos)].slice(0,6), naamloosTotaal:naamloos.length,
                  langAttrs:[...document.querySelectorAll('[lang]')].map(e=>e.tagName+':'+e.getAttribute('lang')).slice(0,4)};
        }""",
                path,
            )
        )
    res["links_labels"] = out

    # 1.3.5 autocomplete + 3.3.2 labels bij invoervelden
    pg.goto(BASE + "/beheer/gebruikers/", wait_until="networkidle")
    pg.wait_for_timeout(900)
    res["formulier"] = pg.evaluate("""() => {
      const out={inputs:0, zonderLabel:[], metAutocomplete:0};
      const walk=(r)=>{ r.querySelectorAll('input,select,textarea').forEach(el=>{
          if(['hidden','submit','button'].includes(el.type)) return;
          out.inputs++;
          if(el.autocomplete && el.autocomplete!=='off') out.metAutocomplete++;
          const id=el.id; const lab=id?document.querySelector('label[for="'+CSS.escape(id)+'"]'):null;
          const naam=el.getAttribute('aria-label')||el.getAttribute('aria-labelledby')||(lab?lab.textContent:'')||el.closest('label')?'ja':'';
          if(!naam) out.zonderLabel.push((el.name||el.type||'?'));
        });
        r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
      walk(document); out.zonderLabel=[...new Set(out.zonderLabel)].slice(0,8); return out;
    }""")

    # 2.5.8 Doelgrootte (AA, 24x24) op de hoofdpagina
    pg.goto(BASE + "/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    res["doelgrootte"] = pg.evaluate("""() => {
      const klein=[]; let n=0;
      const walk=(r)=>{ r.querySelectorAll('button,a[href],[role=button],input[type=checkbox]').forEach(el=>{
          const b=el.getBoundingClientRect(); if(b.width===0) return; n++;
          if(b.width<24||b.height<24) klein.push({el:el.tagName.toLowerCase(),
            t:((el.getAttribute&&el.getAttribute('text'))||el.textContent||'').trim().slice(0,20),
            w:Math.round(b.width),h:Math.round(b.height)});
        });
        r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
      walk(document); return {gemeten:n, teKlein:klein.slice(0,8), teKleinTotaal:klein.length};
    }""")

    # 2.2.1 tijdslimieten / 2.3.1 flitsen / 1.4.2 geluid: aanwezigheid van media
    pg.goto(BASE + "/", wait_until="networkidle")
    pg.wait_for_timeout(700)
    res["media"] = pg.evaluate("""() => ({video:document.querySelectorAll('video').length,
       audio:document.querySelectorAll('audio').length, iframe:document.querySelectorAll('iframe').length,
       marquee:document.querySelectorAll('marquee,blink').length,
       metaRefresh:document.querySelectorAll('meta[http-equiv=refresh]').length})""")

    # 1.3.4 weergavestand (portret/landschap)
    pg.set_viewport_size({"width": 600, "height": 900})
    pg.wait_for_timeout(600)
    portret = pg.evaluate("() => document.documentElement.scrollWidth<=document.documentElement.clientWidth+1")
    pg.set_viewport_size({"width": 900, "height": 600})
    pg.wait_for_timeout(600)
    landschap = pg.evaluate("() => document.documentElement.scrollWidth<=document.documentElement.clientWidth+1")
    res["weergavestand"] = {"portret_ok": portret, "landschap_ok": landschap}

    # 1.4.12 Tekstafstand (AA)
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.goto(BASE + "/", wait_until="networkidle")
    pg.wait_for_timeout(800)
    voor = pg.evaluate("() => document.body.scrollHeight")
    pg.add_style_tag(
        content="""* { line-height:1.5 !important; letter-spacing:0.12em !important;
        word-spacing:0.16em !important; } p { margin-bottom:2em !important; }"""
    )
    pg.wait_for_timeout(700)
    res["tekstafstand"] = pg.evaluate(
        """(v) => ({hoogte_voor:v, hoogte_na:document.body.scrollHeight,
        horizontaal:document.documentElement.scrollWidth>document.documentElement.clientWidth+1})""",
        voor,
    )
    b.close()
json.dump(res, open("extra.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:2600])
