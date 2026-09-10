"""Focus na een htmx-swap op de live pagina's, in Chromium, Edge en Firefox.

Meet de flows uit de hertest van 9 september 2026 (rapport, 2.4.3): paneel
openen en sluiten, weergave wisselen, opdracht invoeren, filtergroep-modal en
inline bewerken. Gebruik: python3 hertest_swap.py <sessionid>
"""
import sys
from playwright.sync_api import sync_playwright
SID = sys.argv[1] if len(sys.argv) > 1 else ""
if not SID:
    print("Gebruik: python3 hertest_swap.py <sessionid>"); sys.exit(1)
FOCUS = r"""()=>{let a=document.activeElement; let s=a.tagName; let d=0;
  while(a.shadowRoot&&a.shadowRoot.activeElement&&d<3){a=a.shadowRoot.activeElement;s+='>'+a.tagName;d++;}
  const lbl=(a.getAttribute('aria-label')||a.labels?.[0]?.textContent||a.textContent||'').trim().replace(/\s+/g,' ').slice(0,30);
  return s+'['+lbl+']';}"""

def run_a(name):
    with sync_playwright() as p:
        b = p.chromium.launch() if name=="chromium" else p.firefox.launch() if name=="firefox" else p.chromium.launch(channel="msedge")
        ctx=b.new_context(viewport={'width':1440,'height':900})
        ctx.add_cookies([{'name':'sessionid','value':SID,'domain':'localhost','path':'/'}])
        page=ctx.new_page(); f=lambda: page.evaluate(FOCUS)
        out=[]
        # 1 zijbalkfilter: eerste checkbox in het filterformulier
        page.goto('http://localhost:8080/', wait_until='domcontentloaded'); page.wait_for_timeout(900)
        page.evaluate(r"""()=>{const el=document.querySelector('[data-filter-input]'); (el.shadowRoot?.querySelector('input')||el).focus();}""")
        before=f(); page.keyboard.press('Space'); page.wait_for_timeout(1800); out.append(('zijbalkfilter Space', before, f()))
        # 2 kaart -> paneel
        page.goto('http://localhost:8080/', wait_until='domcontentloaded'); page.wait_for_timeout(900)
        page.evaluate(r"""()=>document.querySelector('nldd-card[hx-get]').shadowRoot.querySelector('a').focus()""")
        before=f(); page.keyboard.press('Enter'); page.wait_for_timeout(1800); out.append(('kaart Enter', before, f()))
        page.keyboard.press('Escape'); page.wait_for_timeout(900); out.append(('paneel Escape', '', f()))
        # 3 weergave-wissel (segmented control)
        page.goto('http://localhost:8080/', wait_until='domcontentloaded'); page.wait_for_timeout(900)
        page.evaluate(r"""()=>{const el=document.querySelectorAll('nldd-segmented-control-item[hx-get]')[1]; (el.shadowRoot?.querySelector('button,input,a')||el).focus();}""")
        before=f(); page.keyboard.press('Enter'); page.wait_for_timeout(1800); out.append(('weergave Enter', before, f()))
        # 4 nieuwe opdracht knop
        page.goto('http://localhost:8080/opdrachten/', wait_until='domcontentloaded'); page.wait_for_timeout(900)
        page.evaluate(r"""()=>document.querySelector('nldd-button[hx-get]').shadowRoot.querySelector('button').focus()""")
        before=f(); page.keyboard.press('Enter'); page.wait_for_timeout(1800); out.append(('nieuwe opdracht Enter', before, f()))
        b.close()
    print(f"=== {name} ===")
    for k,a,c in out: print(f"  {k:24} {a:42} -> {c}")

def run_b(name):
    with sync_playwright() as p:
        b = p.chromium.launch() if name=="chromium" else p.firefox.launch() if name=="firefox" else p.chromium.launch(channel="msedge")
        ctx=b.new_context(viewport={'width':1440,'height':900})
        ctx.add_cookies([{'name':'sessionid','value':SID,'domain':'localhost','path':'/'}])
        page=ctx.new_page(); f=lambda: page.evaluate(FOCUS); out=[]
        # A filtergroep (list-item) -> modal -> Escape
        page.goto('http://localhost:8080/', wait_until='domcontentloaded'); page.wait_for_timeout(900)
        page.evaluate(r"""()=>document.querySelector('nldd-list-item[hx-get*="filter_modal"]').shadowRoot.querySelector('button,a').focus()""")
        before=f(); page.keyboard.press('Enter'); page.wait_for_timeout(1800); mid=f()
        page.keyboard.press('Tab'); tab1=f()
        page.keyboard.press('Escape'); page.wait_for_timeout(900); out.append(('filtergroep Enter', before, mid, 'Tab: '+tab1, 'Esc: '+f()))
        # B inline bewerken in het paneel: kaart -> paneel -> potlood -> Enter -> veld; Escape terug
        page.goto('http://localhost:8080/', wait_until='domcontentloaded'); page.wait_for_timeout(900)
        page.evaluate(r"""()=>document.querySelector('nldd-card[hx-get]').shadowRoot.querySelector('a').focus()""")
        page.keyboard.press('Enter'); page.wait_for_timeout(1800)
        pencil=None
        for i in range(30):
            page.keyboard.press('Tab'); cur=f()
            if 'ewerk' in cur: pencil=cur; break
        page.keyboard.press('Enter'); page.wait_for_timeout(1800); field=f()
        page.keyboard.press('Escape'); page.wait_for_timeout(1200); out.append(('inline bewerken', pencil or 'geen potlood in 30 Tabs', field, 'Esc: '+f(), ''))
        b.close()
    print(f"=== {name} ===")
    for row in out: print('  ' + ' | '.join(str(x) for x in row if x))

for n in ["chromium", "firefox", "msedge"]:
    for fn in (run_a, run_b):
        try: fn(n)
        except Exception as e: print(f"=== {n} === FOUT {str(e)[:140]}")
