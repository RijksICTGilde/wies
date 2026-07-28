// Toolbar + card-list glue for "Wie zit waar?" (CSP: script-src 'self', no inline JS).
//
// 1. Weergave-switch: the nldd-segmented-control emits a `change` event with the
//    picked value. We look up its URL in data-groupby-urls ("value=url;value=url")
//    and navigate there — same full-page nav the base.html menu-items use.
// 2. Pagination dedup: the list pagineert op plaatsingen maar toont cards per
//    persoon/opdracht. Een groep die de paginagrens overlapt zou anders twee keer
//    verschijnen (staart op pagina N, kop op N+1). Na elke htmx-swap gooien we cards
//    weg waarvan de data-group-key al eerder in de lijst staat; we houden de eerste.
(function () {
  "use strict";

  function parseUrlMap(raw) {
    const map = {};
    if (!raw) return map;
    raw.split(";").forEach(function (pair) {
      const idx = pair.indexOf("=");
      if (idx > -1) map[pair.slice(0, idx)] = pair.slice(idx + 1);
    });
    return map;
  }

  // Delegated on document so it survives htmx swaps of the container.
  document.addEventListener("change", function (event) {
    const control = event.target.closest("[data-groupby-switch]");
    if (!control) return;
    const value = event.detail && event.detail.value;
    if (!value) return;
    const url = parseUrlMap(control.getAttribute("data-groupby-urls"))[value];
    if (url) window.location.href = url;
  });

  function dedupCards() {
    document
      .querySelectorAll(".nldd-placement-card-list")
      .forEach(function (list) {
        const seen = new Set();
        list
          .querySelectorAll("nldd-card[data-group-key]")
          .forEach(function (card) {
            const key = card.getAttribute("data-group-key");
            if (seen.has(key)) {
              card.remove();
            } else {
              seen.add(key);
            }
          });
      });
  }

  document.body.addEventListener("htmx:afterSwap", dedupCards);
})();
