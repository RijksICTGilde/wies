// Opent de filtersheet van de gebruikerslijst. De sheet staat server-side in de
// pagina (user_admin.html), niet lazy: het #filter-form erin is wat het zoekveld
// en de filterchips aansturen, en dat moet er dus altijd zijn. Het filteren zelf
// loopt via het gedeelde filter_interactions.js (aanvinken → hidden input →
// form-submit naar #results), dus dit bestand doet alleen openen. Extern bestand
// i.p.v. inline <script> zodat CSP script-src 'self' blijft.
(function () {
  "use strict";

  const SHEET_ID = "user-filter-sheet";
  const OPEN_ATTR = "data-user-filter-open";

  function sheet() {
    return document.getElementById(SHEET_ID);
  }

  // Lit-component: bij een vroege klik bestaat de shadow <dialog> misschien nog
  // niet, dus show() no-opt. Wacht op updateComplete, val terug op rAF.
  function openWhenReady(el, attempt) {
    if (!el) return;
    const tryShow = () => {
      if (
        typeof el.show === "function" &&
        el.shadowRoot?.querySelector("dialog")
      ) {
        el.show();
      } else if ((attempt || 0) < 20) {
        requestAnimationFrame(() => openWhenReady(el, (attempt || 0) + 1));
      }
    };
    if (el.updateComplete?.then) el.updateComplete.then(tryShow);
    else tryShow();
  }

  function init() {
    // Eén gedelegeerde listener voor de knop én het overflow-menu-item. De knop
    // wordt niet meer OOB geswapt, maar delegatie blijft het robuustst.
    document.addEventListener("click", (e) => {
      const trigger = e
        .composedPath()
        .find((el) => el instanceof Element && el.hasAttribute?.(OPEN_ATTR));
      if (!trigger) return;
      e.preventDefault();
      openWhenReady(sheet(), 0);
    });

    // nldd-menu-item vuurt `select`, geen click, als het via het toetsenbord gaat.
    document.addEventListener("select", (e) => {
      const trigger = e
        .composedPath()
        .find((el) => el instanceof Element && el.hasAttribute?.(OPEN_ATTR));
      if (!trigger) return;
      openWhenReady(sheet(), 0);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
