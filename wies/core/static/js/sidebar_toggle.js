// The "Filter" button drives nldd-sidebar-section's own sheet; the component
// owns the collapsing, this only calls show()/toggle() and tracks aria-expanded.
(function () {
  "use strict";

  document.addEventListener("click", (e) => {
    const btn = window.wiesClosestInPath(e, "#sidebar-toggle");
    if (btn) btn.closest("nldd-sidebar-section")?.toggle();
  });

  // The toolbar's overflow menu shows a clone with the same id and reports
  // `select` on the original, so without the contains check this fires twice.
  document.addEventListener("select", (e) => {
    const item = window.wiesClosestInPath(e, "#sidebar-toggle-menu-item");
    if (!item || !document.contains(item)) return;
    // show(), not toggle(): picking a menu item means "open".
    item.closest("nldd-sidebar-section")?.show();
  });

  function reflectExpanded(open) {
    return (e) =>
      e.target
        .querySelectorAll?.("#sidebar-toggle, #sidebar-toggle-menu-item")
        .forEach((el) => el.setAttribute("aria-expanded", String(open)));
  }

  document.addEventListener("open", reflectExpanded(true));
  document.addEventListener("close", reflectExpanded(false));
})();
