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

  // The sidebar collapses at the DS's lg breakpoint (1008px section width),
  // which on this page is far too late: the sidebar keeps its 320px while the
  // toolbar runs out of room, so the controls move into the overflow menu one
  // by one -- sort first, then the view switch -- and only after that does the
  // sidebar collapse and hand all that room back at once.
  //
  // 1240px keeps the filters in view as long as they comfortably fit; below it,
  // folding them away buys back more room than any control needs, so the bar
  // stays out in the open down to ~1070px. The trade is a ~90px stretch
  // (1320-1240) where the sort control sits in the overflow menu while the
  // filters are still open -- the bar never empties out there, only sorting
  // moves, and it stays reachable.
  //
  // _lgMin is a per-instance property, so this moves the threshold for this
  // section only and leaves the component's behaviour everywhere else intact.
  const COLLAPSE_AT = 1240;

  const sections = document.querySelectorAll("nldd-sidebar-section");
  if (sections.length) {
    const observer = new MutationObserver(syncOverflowItem);
    sections.forEach((section) => {
      // whenDefined: this script runs before the DS upgrades the element, and
      // _lgMin only exists once the constructor has run. Guarded so that a
      // renamed field leaves the component's own default in place instead of
      // silently doing nothing.
      customElements.whenDefined("nldd-sidebar-section").then(() => {
        if (typeof section._lgMin !== "number") return;
        section._lgMin = COLLAPSE_AT;
        section._applyCollapsed?.(section.clientWidth, false);
      });
      observer.observe(section, {
        attributes: true,
        attributeFilter: ["collapsed"],
      });
    });
    syncOverflowItem();
  }
  // The toolbar re-renders on an htmx swap, which brings back a fresh item.
  document.body.addEventListener("htmx:afterSwap", syncOverflowItem);
})();
