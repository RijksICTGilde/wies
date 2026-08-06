// Opent de filtersheet van de gebruikerslijst nadat htmx hem in
// #user-filter-container heeft geswapt. Het filteren zelf loopt via het gedeelde
// filter_interactions.js (aanvinken → hidden input → form-submit naar #results),
// dus dit bestand doet alleen openen/sluiten. Extern bestand i.p.v. inline
// <script> zodat CSP script-src 'self' blijft.
(function () {
  "use strict";

  const SHEET_ID = "user-filter-sheet";
  const CONTAINER_ID = "user-filter-container";

  function sheet() {
    return document.getElementById(SHEET_ID);
  }

  // Lit-component: vlak na de swap bestaat de shadow <dialog> nog niet, dus
  // show() no-opt. Wacht op updateComplete, val terug op rAF.
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
    document.body.addEventListener("htmx:afterSwap", (e) => {
      const t = e.target;
      if (t && (t.id === CONTAINER_ID || t.closest?.("#" + CONTAINER_ID))) {
        openWhenReady(sheet(), 0);
      }
    });

    // Leeg de mount na sluiten, zodat opnieuw openen een verse lijst haalt.
    document.addEventListener(
      "close",
      (e) => {
        const s = e
          .composedPath()
          .find((el) => el instanceof Element && el.id === SHEET_ID);
        if (!s) return;
        const c = document.getElementById(CONTAINER_ID);
        if (c) c.innerHTML = "";
      },
      true,
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
