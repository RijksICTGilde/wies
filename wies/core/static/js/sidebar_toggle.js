// The "Filter" button drives nldd-sidebar-section's own sheet; the component
// owns the collapsing, this only calls show()/toggle().
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

  // The toolbar's overflow menu shows a clone with the same id and reports
  // `select` on the original, so without the contains check this fires twice.
  document.addEventListener("select", (e) => {
    const item = window.wiesClosestInPath(e, "#sidebar-toggle-menu-item");
    if (!item || !document.contains(item)) return;
    // show(), not toggle(): picking a menu item means "open".
    showSidebar();
  });
})();
