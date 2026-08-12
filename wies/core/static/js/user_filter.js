// Opens the user list's filter sheet. The sheet is server-rendered because the
// #filter-form inside it drives the search field and chips.
(function () {
  "use strict";

  const SHEET_ID = "user-filter-sheet";
  const OPEN_ATTR = "data-user-filter-open";

  function sheet() {
    return document.getElementById(SHEET_ID);
  }

  // Lit component: on an early click the shadow <dialog> may not exist yet and
  // show() silently no-ops, so wait for updateComplete and fall back to rAF.
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
    // One delegated listener for both the button and the overflow menu item.
    document.addEventListener("click", (e) => {
      const trigger = e
        .composedPath()
        .find((el) => el instanceof Element && el.hasAttribute?.(OPEN_ATTR));
      if (!trigger) return;
      e.preventDefault();
      openWhenReady(sheet(), 0);
    });

    // nldd-menu-item fires `select`, not click, when activated by keyboard.
    document.addEventListener("select", (e) => {
      const trigger = e
        .composedPath()
        .find((el) => el instanceof Element && el.hasAttribute?.(OPEN_ATTR));
      if (!trigger) return;
      openWhenReady(sheet(), 0);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
