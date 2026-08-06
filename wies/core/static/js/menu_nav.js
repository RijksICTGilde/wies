// Navigatie voor nldd-componenten die een data-href dragen: die componenten
// leveren zelf geen link-gedrag, dus we vangen de click (via composedPath, want
// het element zit in een shadow root) en navigeren. Geldt voor menu-items én
// voor een losse nldd-icon-button — een rijactie die de enige actie is, wordt
// als knop getoond in plaats van in een menu. Extern bestand i.p.v. inline
// <script>, zodat de CSP script-src 'self' kan blijven (geen 'unsafe-inline').
const HREF_CARRIERS = new Set(["nldd-menu-item", "nldd-icon-button"]);
document.addEventListener("click", (e) => {
  const item = e
    .composedPath()
    .find(
      (el) =>
        el instanceof Element &&
        HREF_CARRIERS.has(el.localName) &&
        el.dataset &&
        el.dataset.href,
    );
  if (item) window.location.href = item.dataset.href;
});
