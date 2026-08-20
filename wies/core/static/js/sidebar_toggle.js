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

  // With the sidebar in view its filters are already there, so a "Filter" entry
  // in the overflow menu would open what is open. CSS cannot reach it: the
  // toolbar clones the item into its own shadow root, out of reach of document
  // styles. [hidden] travels with the clone, so hide the source instead.
  function syncOverflowItem() {
    document.querySelectorAll("#sidebar-toggle-menu-item").forEach((item) => {
      const collapsed = item
        .closest("nldd-sidebar-section")
        ?.hasAttribute("collapsed");
      item.toggleAttribute("hidden", !collapsed);
    });
  }

  const sections = document.querySelectorAll("nldd-sidebar-section");
  if (sections.length) {
    const observer = new MutationObserver(syncOverflowItem);
    sections.forEach((s) =>
      observer.observe(s, { attributes: true, attributeFilter: ["collapsed"] }),
    );
    syncOverflowItem();
  }
  // The toolbar re-renders on an htmx swap, which brings back a fresh item.
  document.body.addEventListener("htmx:afterSwap", syncOverflowItem);
})();
