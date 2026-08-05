// Sorteermenu in de toolbar.
//
// De opties zijn radio-items: sorteren is één keuze uit een lijst, en alleen
// een radio of checkbox toont zijn selected-staat. Het DS negeert een href op
// zo'n item (het is een keuze, geen navigatie), dus de bestemming staat in
// data-wies-sort-url en dit script doet de navigatie.
//
// Een volledige paginalading en geen htmx-swap: de toolbar rendert alleen bij
// een hele pagina, dus na een swap zouden de knoptekst en het aangevinkte item
// de vorige sortering blijven tonen.
(function () {
  "use strict";

  document.addEventListener("select", (e) => {
    const item = e
      .composedPath()
      .find(
        (el) => el instanceof Element && el.hasAttribute("data-wies-sort-url"),
      );
    if (!item) return;
    // Het overflowmenu van de toolbar toont een KLOON en meldt de keuze daarna
    // nog eens op het origineel. Zonder deze check navigeren we twee keer.
    if (!document.contains(item)) return;
    window.location.assign(item.getAttribute("data-wies-sort-url"));
  });
})();
