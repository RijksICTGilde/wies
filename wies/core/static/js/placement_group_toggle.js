(function () {
  // Fold-out group header (variant "groups"): expand/collapse the member rows.
  function toggleGroup(header) {
    const expanded = header.getAttribute("aria-expanded") !== "false";
    const next = !expanded;
    header.setAttribute("aria-expanded", String(next));

    let row = header.nextElementSibling;
    while (row && !row.hasAttribute("data-group-header")) {
      if (row.hasAttribute("data-group-member")) {
        row.classList.toggle("is-collapsed", !next);
      }
      row = row.nextElementSibling;
    }
  }

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
    // Fold-out group header toggle.
    const header = event.target.closest("[data-group-header]");
    if (header) {
      toggleGroup(header);
      return;
    }

    // View/sort menu open/close.
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
    if (event.key === "Escape") {
      closeAllGroupbyMenus();
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") return;
    const header = event.target.closest("[data-group-header]");
    if (header && event.target === header) {
      event.preventDefault();
      toggleGroup(header);
    }
  });
})();
