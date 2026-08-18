// Keeps the sidebar box within the viewport: sticky-top feeds both `top` and
// `max-height`, which only lines up when the bar above it is sticky too.

const GAP = 16;

const BOX_CSS = `
.sidebar-section__sidebar-box {
  top: ${GAP}px;
  max-height: calc(100dvh - var(--_live-top, ${GAP}px) - ${GAP}px);
}
`;

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

  // Where the box sits is exactly the space lost above it.
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

function patchAll() {
  for (const section of document.querySelectorAll("nldd-sidebar-section")) {
    if (section.shadowRoot) {
      applyStickyOffsets(section);
    } else {
      customElements.whenDefined("nldd-sidebar-section").then(() => {
        // Lit renders its shadow root a tick after definition.
        (section.updateComplete ?? Promise.resolve()).then(() =>
          applyStickyOffsets(section),
        );
      });
    }
  }
}

document.addEventListener("DOMContentLoaded", patchAll);
patchAll();
