// Opent de bord-filter-sheet vanaf de "Filter"-knop.
//
// De knop draagt data-open-board-filters; de sheet is #filter-sheet. We wachten
// op de nldd-sheet-upgrade + updateComplete voordat we show() aanroepen — anders
// faalt show() stil vlak na het laden (zelfde timing als side_panel.js).
// CSP-veilig: gedelegeerde listener in dit bestand, geen inline handlers.
(function () {
  "use strict";

  async function openSheet(sheet) {
    if (!sheet) return;
    if (window.customElements) {
      await window.customElements.whenDefined("nldd-sheet");
    }
    if (sheet.updateComplete) await sheet.updateComplete;
    if (typeof sheet.show === "function") sheet.show();
  }

  document.addEventListener("click", (e) => {
    const btn = e
      .composedPath()
      .find(
        (el) =>
          el instanceof Element && el.hasAttribute("data-open-board-filters"),
      );
    if (!btn) return;
    openSheet(document.getElementById("filter-sheet"));
  });
})();
