// Opens the user list's filter sheet. The sheet is server-rendered because the
// #filter-form inside it drives the search field and chips.
(function () {
  "use strict";

  const SHEET_ID = "user-filter-sheet";
  const OPEN_ATTR = "data-user-filter-open";

  function sheet() {
    return document.getElementById(SHEET_ID);
  }

  function openSheet() {
    sheet()?.show();
  }

  function init() {
    // One delegated listener for both the button and the overflow menu item.
    document.addEventListener("click", (e) => {
      const trigger = e
        .composedPath()
        .find((el) => el instanceof Element && el.hasAttribute?.(OPEN_ATTR));
      if (!trigger) return;
      e.preventDefault();
      openSheet();
    });

    // nldd-menu-item fires `select`, not click, when activated by keyboard.
    document.addEventListener("select", (e) => {
      const trigger = e
        .composedPath()
        .find((el) => el instanceof Element && el.hasAttribute?.(OPEN_ATTR));
      if (!trigger) return;
      openSheet();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
