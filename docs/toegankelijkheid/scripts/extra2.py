"""Sluit een paar openstaande criteria: 1.4.11 (niet-tekstueel contrast),
2.1.2 (toetsenbordval in modal), 4.1.3 (live regions), 404-pagina."""

import json

from playwright.sync_api import sync_playwright


def lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    l1, l2 = lum(a), lum(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()

    # --- 404-pagina (ontbrak in de steekproef)
    r = pg.goto("http://localhost:8080/bestaat-echt-niet-xyz/", wait_until="networkidle")
    pg.wait_for_timeout(800)
    res["404"] = pg.evaluate(
        """(s) => ({status:s, lang:document.documentElement.lang, titel:document.title,
        h1:document.querySelectorAll('h1').length,
        h1tekst:(document.querySelector('h1')||{}).textContent||null,
        tekst:document.body.innerText.replace(/\\s+/g,' ').slice(0,150)})""",
        r.status if r else 0,
    )

    # --- 1.4.11 niet-tekstueel contrast: randen van invoervelden en knoppen
    pg.goto("http://localhost:8080/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    cols = pg.evaluate("""() => {
      const cv=document.createElement('canvas'); cv.width=cv.height=1;
      const cx=cv.getContext('2d',{willReadFrequently:true});
      const rgba=(c)=>{cx.clearRect(0,0,1,1); cx.fillStyle='#000'; cx.fillStyle=c; cx.fillRect(0,0,1,1);
        const d=cx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2],d[3]/255];};
      const out=[];
      const walk=(r)=>{ r.querySelectorAll('input,button,select,textarea,[role=checkbox],[role=button]').forEach(el=>{
          const bb=el.getBoundingClientRect(); if(bb.width<4||bb.height<4) return;
          const cs=getComputedStyle(el);
          const bc=rgba(cs.borderTopColor), bg=rgba(cs.backgroundColor);
          if(cs.borderTopWidth==='0px' && bg[3]===0) return;
          out.push({tag:el.tagName.toLowerCase(),
                    border:[bc[0],bc[1],bc[2],bc[3]], bw:cs.borderTopWidth,
                    bg:[bg[0],bg[1],bg[2],bg[3]]});
        });
        r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
      walk(document); return out.slice(0,40);
    }""")
    laag = []
    for c in cols:
        if c["border"][3] > 0 and c["bw"] != "0px":
            r_ = ratio(c["border"][:3], [255, 255, 255])
            if r_ < 3.0:
                laag.append({"tag": c["tag"], "ratio": round(r_, 2), "bw": c["bw"]})
    res["niet_tekstueel_contrast"] = {"gemeten": len(cols), "onder_3:1": laag[:8], "aantal_onder": len(laag)}

    # --- 2.1.2 toetsenbordval: open een modal en tab er doorheen
    pg.goto("http://localhost:8080/beheer/merken/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    opened = pg.evaluate("""() => { const b=[...document.querySelectorAll('nldd-button')]
        .find(x=>/toevoegen/i.test(x.getAttribute('text')||'')); if(!b) return false;
        b.shadowRoot?.querySelector('button')?.click() ?? b.click(); return true; }""")
    pg.wait_for_timeout(1500)
    seq = []
    for i in range(14):
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(90)
        seq.append(
            pg.evaluate("""() => { let a=document.activeElement;
          while(a&&a.shadowRoot&&a.shadowRoot.activeElement) a=a.shadowRoot.activeElement;
          const inModal = !!(a && a.closest && (a.closest('nldd-modal-dialog')||a.closest('nldd-sheet')||a.closest('[role=dialog]')));
          return {tag:a?a.tagName.toLowerCase():null, inModal}; }""")
        )
    res["toetsenbordval"] = {
        "modal_geopend": opened,
        "stops": len(seq),
        "binnen_modal": sum(1 for s in seq if s["inModal"]),
        "buiten_modal": sum(1 for s in seq if not s["inModal"]),
    }

    # --- 4.1.3 statusberichten: bestaan er live regions?
    pg.goto("http://localhost:8080/", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    res["live_regions"] = pg.evaluate("""() => {
      const out=[]; const walk=(r)=>{ r.querySelectorAll('[aria-live],[role=status],[role=alert],output').forEach(el=>{
          out.push({tag:el.tagName.toLowerCase(), live:el.getAttribute('aria-live'),
                    role:el.getAttribute('role'), tekst:(el.textContent||'').trim().slice(0,40)}); });
        r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) walk(e.shadowRoot); }); };
      walk(document); return out; }""")
    b.close()
json.dump(res, open("extra2.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:1800])
