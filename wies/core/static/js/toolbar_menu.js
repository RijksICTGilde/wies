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

  // "Wie zit waar?" pagineert op plaatsingen, maar toont cards per persoon/opdracht.
  // Een groep die de paginagrens overlapt zou anders twee keer verschijnen (staart
  // op pagina N, kop op pagina N+1). Na elke "meer laden"-swap gooien we cards weg
  // waarvan de data-group-key al eerder in de lijst staat; we houden de eerste.
  // Kanttekening: bij zo'n overlappende groep toont de overgebleven card alleen de
  // plaatsingen van díé pagina, dus mogelijk incompleet — zeldzaam en zichtbaar acceptabel.
  document.body.addEventListener("htmx:afterSwap", function () {
    // outerHTML-swapping the "meer laden"-sentinel leaves no stable event target,
    // so just re-scan every card list on the page; on a single-page list it's a no-op.
    document.querySelectorAll(".wzw-card-list").forEach(function (list) {
      const seen = new Set();
      list
        .querySelectorAll(".wzw-card[data-group-key]")
        .forEach(function (card) {
          const key = card.getAttribute("data-group-key");
          if (seen.has(key)) {
            card.remove();
          } else {
            seen.add(key);
          }
        });
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeAllGroupbyMenus();
      return;
    }
    // Enter on a keyboard-focused card (role="link" + hx-get) opens the side
    // panel, mirroring a mouse click. Delegated so it survives HTMX swaps.
    if (event.key === "Enter") {
      const card = event.target.closest(".wzw-card[hx-get]");
      if (card && event.target === card) {
        event.preventDefault();
        window.htmx.trigger(card, "click");
      }
    }
  });
})();
