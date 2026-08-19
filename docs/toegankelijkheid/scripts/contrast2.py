"""Contrast (WCAG 1.4.3 AA) incl. shadow DOM. Colours converted by the browser
itself via canvas, so oklch()/lab() resolve to real sRGB instead of being parsed."""

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
    "/faq/",
    "/contact/",
    "/privacy/",
    "/toegankelijkheid/",
    "/profiel/",
]

COLLECT = r"""() => {
  const cv=document.createElement('canvas'); cv.width=cv.height=1;
  const cx=cv.getContext('2d',{willReadFrequently:true});
  const rgba=(c)=>{ cx.clearRect(0,0,1,1); cx.fillStyle='#000'; cx.fillStyle=c;
    cx.fillRect(0,0,1,1); const d=cx.getImageData(0,0,1,1).data;
    return [d[0],d[1],d[2],d[3]/255]; };
  const bgStack=(el)=>{ const st=[]; let n=el;
    while(n){ const cs=getComputedStyle(n); const c=rgba(cs.backgroundColor);
      if(c[3]>0) st.push(c); if(c[3]===1) return st;
      n=n.parentElement||(n.getRootNode()||{}).host; }
    st.push([255,255,255,1]); return st; };
  const flat=(st)=>{ let r=[255,255,255];
    for(let i=st.length-1;i>=0;i--){ const c=st[i], a=c[3];
      r=[c[0]*a+r[0]*(1-a), c[1]*a+r[1]*(1-a), c[2]*a+r[2]*(1-a)]; }
    return r; };
  const out=[];
  const walk=(root)=>{ root.querySelectorAll('*').forEach(el=>{
      if(el.shadowRoot) walk(el.shadowRoot);
      const txt=[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ').trim();
      if(!txt) return;
      const r=el.getBoundingClientRect(); if(r.width===0||r.height===0) return;
      const cs=getComputedStyle(el);
      if(cs.visibility==='hidden'||cs.display==='none') return;
      let op=1, n=el;
      while(n){ op*=parseFloat(getComputedStyle(n).opacity); n=n.parentElement||(n.getRootNode()||{}).host; }
      if(op<0.05) return;
      const fg=rgba(cs.color), bg=flat(bgStack(el));
      const a=fg[3]*op;
      out.push({tag:el.tagName.toLowerCase(), text:txt.slice(0,70),
        fg:[fg[0]*a+bg[0]*(1-a), fg[1]*a+bg[1]*(1-a), fg[2]*a+bg[2]*(1-a)], bg,
        size:parseFloat(cs.fontSize), weight:parseInt(cs.fontWeight)||400,
        shadow: root!==document});
    }); };
  walk(document);
  return out;
}"""


def lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    l1, l2 = lum(a), lum(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


fails = []
total = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
    for path in PAGES:
        pg.goto(BASE + path, wait_until="networkidle")
        pg.wait_for_timeout(1100)
        for it in pg.evaluate(COLLECT):
            total += 1
            r = ratio(it["fg"], it["bg"])
            large = it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)
            need = 3.0 if large else 4.5
            if r < need - 0.05:
                fails.append(
                    {
                        "page": path,
                        "tag": it["tag"],
                        "text": it["text"],
                        "ratio": round(r, 2),
                        "need": need,
                        "size": round(it["size"], 1),
                        "shadow": it["shadow"],
                        "fg": [round(x) for x in it["fg"]],
                        "bg": [round(x) for x in it["bg"]],
                    }
                )
    b.close()

json.dump(fails, open("contrast.json", "w"), indent=1)
print(f"tekstelementen gemeten : {total}")
print(f"onder de norm          : {len(fails)}")
seen = set()
for f in sorted(fails, key=lambda x: x["ratio"]):
    k = (f["tag"], f["text"][:28])
    if k in seen:
        continue
    seen.add(k)
    print(
        f"  {f['ratio']:5.2f}:1 (min {f['need']}) {'[shadow]' if f['shadow'] else '        '} <{f['tag']}> {f['text'][:40]!r}  {f['page']}"
    )
