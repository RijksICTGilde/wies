// Sidebar collapse toggle. The "Filters" button (#sidebar-toggle) drives the
// <nldd-sidebar-section>'s own sheet: a sticky aside on wide screens, a left
// sheet when narrower.
(function () {
  "use strict";

  function sidebarSection() {
    return document.querySelector("nldd-sidebar-section");
  }

  function toggleSidebar() {
    const section = sidebarSection();
    if (section && typeof section.toggle === "function") section.toggle();
  }

  function showSidebar() {
    const section = sidebarSection();
    if (section && typeof section.show === "function") section.show();
  }

  document.addEventListener("click", (e) => {
    if (!window.wiesClosestInPath(e, "#sidebar-toggle")) return;
    toggleSidebar();
  });

  // Same, from the toolbar overflow menu, which shows a clone of the menu item
  // and reports the choice as `select` on the original — a click never reaches
  // it. The clone keeps the id, so without the document.contains check this
  // fires twice (clone in the toolbar's shadow root, then original) and the
  // sidebar opens and closes again.
  document.addEventListener("select", (e) => {
    const item = window.wiesClosestInPath(e, "#sidebar-toggle-menu-item");
    if (!item || !document.contains(item)) return;
    // show(), not toggle(): picking a menu item means "open".
    showSidebar();
  });
})();
