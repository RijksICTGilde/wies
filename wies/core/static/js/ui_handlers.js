// Delegated UI handlers, registered once on `document`. Delegation (rather than
// per-element listeners) keeps these working for HTMX-swapped fragments (side
// panel, cards, event blocks) without re-binding, and lets the templates drop
// their inline on*= attributes so script-src no longer needs 'unsafe-inline'.

(function () {
  // Forms that confirm before submitting: <form data-confirm="..."> cancels the
  // submit if the user declines. Replaces onsubmit="return confirm(...)".
  document.addEventListener("submit", function (event) {
    var form = event.target.closest("form[data-confirm]");
    if (form && !window.confirm(form.getAttribute("data-confirm"))) {
      event.preventDefault();
    }
  });

  // Keyboard activation of clickable assignment cards: Enter triggers the same
  // htmx "click" the mouse would. The card carries hx-get/hx-target itself.
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter") return;
    var card = event.target.closest(".assignment-card--clickable");
    if (card && window.htmx) {
      window.htmx.trigger(card, "click");
    }
  });

  document.addEventListener("click", function (event) {
    var menuToggle = event.target.closest(".menubar__mobile-toggle");
    if (menuToggle) {
      var menubar = menuToggle.closest(".menubar");
      if (menubar) menubar.classList.toggle("menubar--mobile-open");
      return;
    }

    // Side-panel close/back call functions defined in side_panel.js, which is
    // only loaded on pages that use the panel; guard so a stray click elsewhere
    // is a no-op.
    if (event.target.closest(".js-side-panel-close")) {
      if (typeof closeSidePanel === "function") closeSidePanel();
      return;
    }
    if (event.target.closest(".js-side-panel-back")) {
      if (typeof panelBack === "function") panelBack();
      return;
    }

    var showMore = event.target.closest(".show-more-toggle");
    if (showMore && typeof toggleShowMore === "function") {
      toggleShowMore(showMore);
    }
  });
})();
