// De filterbox van nldd-sidebar-section leidt twee dingen af uit één waarde:
// `top: var(--_sticky-top)` (waar hij blijft plakken) en
// `max-height: calc(100dvh - var(--_sticky-top) - var(--_sticky-bottom))`
// (hoe hoog hij mag worden). Voor Wies moeten die twee uit elkaar.
//
// De nldd-top-navigation-bar staat boven de box en is `position: static`, dus
// hij scrollt weg. Bovenaan de pagina begint de box daardoor op y=188, maar hij
// hoort te plakken op 16. Eén waarde kan dat niet dekken: op 16 wordt de box te
// hoog en valt zijn onderkant bovenaan de pagina buiten beeld (de onderste
// filtergroep was dan onbereikbaar zonder eerst de pagina te scrollen); op 188
// past de hoogte, maar dan houdt hij ook 188px lege ruimte boven zich zodra de
// navbar weg is.
//
// Dus: `top` vast op de plakhoogte, en de max-height per scrollpositie
// herrekend vanaf waar de box op dat moment staat. De box vult zo altijd tot
// GAP boven de schermrand, en groeit terwijl de navbar wegscrolt (op een
// viewport van 800px: 596px bovenaan, 768px zodra de navbar weg is). Beide
// zitten in de shadow root en dragen geen `part`, dus een adopted stylesheet is
// de enige ingang; vandaar dat dit JS is en geen regel in app.css.
//
// Vervalt zodra de navigatiebalk zelf sticky is (of nldd-app-view de
// scroll-context zet): dan is de starthoogte constant en volstaat het
// sticky-top-attribuut.

const GAP = 16; // marge boven en onder de box, gelijk aan de default sticky-inset

const BOX_CSS = `
.sidebar-section__sidebar-box {
  top: ${GAP}px;
  max-height: calc(100dvh - var(--_live-top, ${GAP}px) - ${GAP}px);
}
`;

/**
 * Koppelt de plakhoogte los van de hoogteberekening op één sidebar-section, en
 * houdt de hoogte bij tijdens het scrollen.
 *
 * @param {Element} section Een nldd-sidebar-section met een shadow root.
 * @returns {void}
 */
function applyStickyOffsets(section) {
  if (!section.shadowRoot || section.dataset.stickyPatched === "true") return;

  const sheet = new CSSStyleSheet();
  sheet.replaceSync(BOX_CSS);
  section.shadowRoot.adoptedStyleSheets = [
    ...section.shadowRoot.adoptedStyleSheets,
    sheet,
  ];
  section.dataset.stickyPatched = "true";

  const box = section.shadowRoot.querySelector(".sidebar-section__sidebar-box");
  if (!box) return;

  // Waar de box nu staat, is precies de ruimte die boven hem verloren gaat.
  // Zolang hij nog niet plakt zakt die waarde mee met de scroll; daarna blijft
  // hij op GAP staan en heeft de box de volle hoogte.
  const syncHeight = () => {
    const top = Math.max(GAP, Math.round(box.getBoundingClientRect().top));
    section.style.setProperty("--_live-top", `${top}px`);
  };

  syncHeight();

  // nldd-page is de scroller, niet het venster (zie app.css: html/body height 100%).
  const scroller = document.querySelector("nldd-page") ?? window;
  scroller.addEventListener("scroll", syncHeight, { passive: true });
  window.addEventListener("resize", syncHeight, { passive: true });
}

/**
 * Patcht elke sidebar-section op de pagina zodra zijn shadow root bestaat.
 *
 * @returns {void}
 */
function patchAll() {
  for (const section of document.querySelectorAll("nldd-sidebar-section")) {
    if (section.shadowRoot) {
      applyStickyOffsets(section);
    } else {
      // Het component is nog niet ge-upgrade; probeer het opnieuw na definitie.
      customElements.whenDefined("nldd-sidebar-section").then(() => {
        // updateComplete: Lit rendert zijn shadow root pas in een latere tick.
        (section.updateComplete ?? Promise.resolve()).then(() =>
          applyStickyOffsets(section),
        );
      });
    }
  }
}

document.addEventListener("DOMContentLoaded", patchAll);
patchAll();
