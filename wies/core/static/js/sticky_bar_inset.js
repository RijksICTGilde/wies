// The sticky header and footer of nldd-page cover what the page scrolls to on
// focus (WCAG 2.4.11): its scroller does not count them. That scroller is a div
// in the shadow root, out of app.css's reach, so the rule goes in as an
// adopted sheet. Only with sticky-header: without it the host itself scrolls
// and .page__scroll is not the scroller. The component publishes both bar
// heights itself, so a bar that grows (search field, selection tokens) is
// followed. The 24 is the fade it draws above the footer; the 32 keeps a
// field's label above it in view, not just the field.
(function () {
  const SELECTOR = "nldd-page[sticky-header]";
  const inset = new CSSStyleSheet();
  inset.replaceSync(`
    .page__scroll {
      scroll-padding-top: calc(var(--_page-header-height, 0px) + var(--primitives-space-32, 32px));
      scroll-padding-bottom: calc(var(--_page-footer-height, 0px) + var(--primitives-space-24, 24px));
    }
  `);

  function addInset(page) {
    const root = page.shadowRoot;
    if (!root || root.adoptedStyleSheets.includes(inset)) return;
    root.adoptedStyleSheets = [...root.adoptedStyleSheets, inset];
  }

  htmx.onLoad(function (elt) {
    const pages = Array.from(elt.querySelectorAll(SELECTOR));
    if (elt.matches(SELECTOR)) pages.push(elt);
    if (!pages.length) return;
    customElements.whenDefined("nldd-page").then(() => pages.forEach(addInset));
  });
})();
