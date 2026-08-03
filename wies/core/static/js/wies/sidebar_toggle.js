// Sidebar collapse toggle.
//
// The "Filters" button (#sidebar-toggle) drives the
// <nldd-sidebar-section>'s own sheet: the section renders the sidebar as a
// sticky aside on wide screens and collapses it to a left sheet when narrower.
(function () {
  "use strict";

  document.addEventListener("click", (e) => {
    const btn = e
      .composedPath()
      .find((el) => el instanceof Element && el.id === "sidebar-toggle");
    if (!btn) return;
    const section = document.querySelector("nldd-sidebar-section");
    if (section && typeof section.toggle === "function") section.toggle();
  });
})();
