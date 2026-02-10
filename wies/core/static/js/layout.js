// Layout constants - read from CSS custom properties (single source of truth)
const LAYOUT = {
  get MOBILE_BREAKPOINT() {
    return (
      parseInt(
        getComputedStyle(document.documentElement).getPropertyValue(
          "--breakpoint-mobile",
        ),
      ) || 800
    );
  },
  get ANIMATION_DURATION_MS() {
    return (
      parseInt(
        getComputedStyle(document.documentElement).getPropertyValue(
          "--animation-duration-ms",
        ),
      ) || 400
    );
  },
};

// Layout Functions

function toggleMobileMenu() {
  const menubar = document.querySelector(".menubar");
  if (menubar) {
    menubar.classList.toggle("menubar--mobile-open");
  }
}

function toggleFilters() {
  const layout = document.getElementById("layout");
  const isMobile = window.innerWidth <= LAYOUT.MOBILE_BREAKPOINT;

  if (isMobile) {
    // Mobile: toggle full screen overlay
    layout.classList.toggle("layout--mobile-filters-open");
  } else {
    // Desktop: toggle collapsed state
    const isCollapsed = layout.classList.toggle("layout--collapsed");

    // Update URL without page reload
    const url = new URL(window.location);
    if (isCollapsed) {
      url.searchParams.set("filters", "0");
    } else {
      url.searchParams.delete("filters");
    }
    history.replaceState({}, "", url);
  }
}

// Overlay close registry - page scripts register their close handlers here.
// Handlers are checked in order; the first matching handler closes its overlay.
const overlayCloseHandlers = [];

function registerOverlayClose(checkFn, closeFn) {
  overlayCloseHandlers.push({ check: checkFn, close: closeFn });
}

// Built-in handlers: mobile filters and mobile menu
registerOverlayClose(
  () => {
    const layout = document.getElementById("layout");
    return layout && layout.classList.contains("layout--mobile-filters-open");
  },
  () => {
    document
      .getElementById("layout")
      .classList.remove("layout--mobile-filters-open");
  },
);

registerOverlayClose(
  () => {
    const menubar = document.querySelector(".menubar");
    return menubar && menubar.classList.contains("menubar--mobile-open");
  },
  () => {
    document.querySelector(".menubar").classList.remove("menubar--mobile-open");
  },
);

// Global ESC key handler - delegates to registered overlay handlers
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    for (const handler of overlayCloseHandlers) {
      if (handler.check()) {
        handler.close();
        return;
      }
    }
  }
});
