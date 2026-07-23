(function () {
  // Open/close the toolbar dropdown menus (view + sort) above the results.
  function closeAllGroupbyMenus() {
    document.querySelectorAll("[data-groupby-menu]").forEach(function (menu) {
      const trigger = menu.querySelector("[data-groupby-trigger]");
      const dropdown = menu.querySelector(".groupby-menu__dropdown");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
      if (dropdown) dropdown.setAttribute("hidden", "");
    });
  }

  // Delegated on document so it survives HTMX swaps of the table container.
  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-groupby-trigger]");
    if (trigger) {
      const menu = trigger.closest("[data-groupby-menu]");
      const dropdown = menu.querySelector(".groupby-menu__dropdown");
      const open = trigger.getAttribute("aria-expanded") === "true";
      closeAllGroupbyMenus();
      if (!open) {
        trigger.setAttribute("aria-expanded", "true");
        dropdown.removeAttribute("hidden");
      }
      return;
    }

    // Any other click (including a menu option, which then HTMX-swaps) closes menus.
    closeAllGroupbyMenus();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeAllGroupbyMenus();
  });
})();
