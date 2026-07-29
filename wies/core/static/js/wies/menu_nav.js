// Navigatie voor nldd-menu-item's die een data-href dragen: het component levert
// zelf geen link-gedrag, dus we vangen de click (via composedPath, want het item
// zit in een shadow root) en navigeren. Extern bestand i.p.v. inline <script>,
// zodat de CSP script-src 'self' kan blijven (geen 'unsafe-inline').
document.addEventListener("click", (e) => {
  const item = e
    .composedPath()
    .find(
      (el) =>
        el instanceof Element &&
        el.localName === "nldd-menu-item" &&
        el.dataset &&
        el.dataset.href,
    );
  if (item) window.location.href = item.dataset.href;
});
