"""Koppenstructuur, tabvolgorde en JavaScript-fouten op de live pagina's,
in Chromium, Edge en Firefox. Hertest van 9 september 2026.

Gebruik: python3 hertest_browsers.py <sessionid>
"""
import json, sys
from playwright.sync_api import sync_playwright
import sys
SID = sys.argv[1] if len(sys.argv) > 1 else ""
PAGES=["/", "/opdrachten/", "/beheer/gebruikers/", "/profiel/", "/faq/"]
HEAD=r"""()=>{const hs=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h=>+h.tagName[1]);
  let skips=0; for(let i=1;i<hs.length;i++){ if(hs[i]>hs[i-1]+1) skips++; }
  return {h1:hs.filter(x=>x===1).length, skips, first:hs.slice(0,4)};}"""
FOCUS=r"""()=>{let a=document.activeElement; let s=a.tagName; let d=0;
  while(a.shadowRoot&&a.shadowRoot.activeElement&&d<3){a=a.shadowRoot.activeElement;s+='>'+a.tagName;d++;} return s;}"""
def engine(p, name):
    if name=="Chromium": return p.chromium.launch()
    if name=="Edge": return p.chromium.launch(channel="msedge")
    return p.firefox.launch()
out={}
with sync_playwright() as p:
    for name in ["Chromium","Edge","Firefox"]:
        try:
            b=engine(p,name); ctx=b.new_context(viewport={"width":1440,"height":900})
            ctx.add_cookies([{"name":"sessionid","value":SID,"domain":"localhost","path":"/"}])
            page=ctx.new_page(); page.set_default_timeout(15000)
            errs=[]; page.on("pageerror", lambda e: errs.append(str(e)))
            res={"version":b.version,"pages":{}}
            for url in PAGES:
                page.goto("http://localhost:8080"+url, wait_until="domcontentloaded"); page.wait_for_timeout(800)
                h=page.evaluate(HEAD)
                stops=[]
                for _ in range(25):
                    page.keyboard.press("Tab"); f=page.evaluate(FOCUS)
                    if f=="BODY": break
                    stops.append(f)
                res["pages"][url]={"h1":h["h1"],"skips":h["skips"],"first":h["first"],"tabstops":len(stops),"first_stop":stops[0] if stops else "-","js_errors":len(errs)}
                errs.clear()
            out[name]=res; b.close()
        except Exception as e:
            out[name]={"error":str(e)[:160]}
json.dump(out, open("main_quick.json","w"), indent=1)
for name,res in out.items():
    print(f"=== {name} {res.get('version','')} ===")
    if "error" in res: print("  FOUT", res["error"]); continue
    for url,d in res["pages"].items():
        print(f"  {url:22} h1={d['h1']} sprongen={d['skips']} eerste={d['first']} tabstops={d['tabstops']:>2} eerste stop={d['first_stop']} js={d['js_errors']}")
