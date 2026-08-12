// nldd-sidebar-section derives both `top` and `max-height` of its filter box
// from --_sticky-top, but the navigation bar above it is static and scrolls
// away, so those need different values. Pin `top` and recompute max-height per
// scroll position instead. Both live in the shadow root and carry no `part`,
// hence an adopted stylesheet rather than a rule in app.css. Obsolete once the
// navigation bar is sticky itself.

const GAP = 16; // Matches the component's default sticky inset.

const BOX_CSS = `
.sidebar-section__sidebar-box {
  top: ${GAP}px;
  max-height: calc(100dvh - var(--_live-top, ${GAP}px) - ${GAP}px);
}
`;

/**
 * Decouples the sticky offset from the height calculation on one section, and
 * keeps the height in sync while scrolling.
 *
 * @param {Element} section An nldd-sidebar-section with a shadow root.
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

  // Where the box sits is exactly the space lost above it: that value follows
  // the scroll until the box sticks, after which it stays at GAP.
  const syncHeight = () => {
    const top = Math.max(GAP, Math.round(box.getBoundingClientRect().top));
    section.style.setProperty("--_live-top", `${top}px`);
  };

  syncHeight();

  // nldd-page is the scroller, not the window (app.css sets html/body to 100%).
  const scroller = document.querySelector("nldd-page") ?? window;
  scroller.addEventListener("scroll", syncHeight, { passive: true });
  window.addEventListener("resize", syncHeight, { passive: true });
}

/**
 * Patches every sidebar-section on the page once its shadow root exists.
 *
 * @returns {void}
 */
function patchAll() {
  for (const section of document.querySelectorAll("nldd-sidebar-section")) {
    if (section.shadowRoot) {
      applyStickyOffsets(section);
    } else {
      // Not upgraded yet; retry once the element is defined.
      customElements.whenDefined("nldd-sidebar-section").then(() => {
        // Lit renders its shadow root a tick later, hence updateComplete.
        (section.updateComplete ?? Promise.resolve()).then(() =>
          applyStickyOffsets(section),
        );
      });
    }
  }
}

document.addEventListener("DOMContentLoaded", patchAll);
patchAll();
