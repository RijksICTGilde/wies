// Delegated UI handlers, registered once on `document`.
//
// Bindings are declared in the markup as data-attributes (`data-action`,
// `data-confirm`, `data-keyboard-activate`) and resolved here, so the element
// still says what it does without needing an inline on*= attribute — those
// would force 'unsafe-inline' back into script-src. Delegation also keeps the
// bindings alive across HTMX swaps (side panel, cards, event blocks) without
// re-binding.
//
// Adding a UI interaction: give the element data-action="<name>" and add the
// matching entry to CLICK_ACTIONS below. Never reach for on*= or <c-... @click>;
// the CSP blocks those silently and test_templates_no_inline_js.py fails the build.
//
// These listeners sit on `document`, so htmx's own element-level listeners have
// already run by the time they fire. They therefore never call preventDefault or
// stopPropagation on a click, and never skip on `defaultPrevented` — htmx
// cancels the native event on every element it drives, so treating "already
// cancelled" as "already handled" would silently drop actions on any element
// that carries both hx-* and data-action.

(function () {
  // Side-panel actions call into side_panel.js, which is only loaded on pages
  // that use the panel; guard so the same markup elsewhere is a no-op.
  var CLICK_ACTIONS = {
    "menu-toggle": function (el) {
      var menubar = el.closest(".menubar");
      if (menubar) menubar.classList.toggle("menubar--mobile-open");
    },
    "side-panel-close": function () {
      if (typeof closeSidePanel === "function") closeSidePanel();
    },
    "side-panel-back": function () {
      if (typeof panelBack === "function") panelBack();
    },
    "show-more": function (el) {
      if (typeof toggleShowMore === "function") toggleShowMore(el);
    },
  };

  // event.target is an Element for user-driven events, but not for events
  // dispatched at document/window, so route every lookup through this.
  function closestFrom(event, selector) {
    var target = event.target;
    return target && target.closest ? target.closest(selector) : null;
  }

  // Forms that confirm before submitting: <form data-confirm="..."> cancels the
  // submit if the user declines. Plain forms only — htmx issues its request from
  // its own submit listener, which runs before this one, so a confirm here could
  // not call it back. Use hx-confirm on htmx-driven forms.
  document.addEventListener("submit", function (event) {
    var form = closestFrom(event, "form[data-confirm]");
    if (form && !window.confirm(form.getAttribute("data-confirm"))) {
      event.preventDefault();
    }
  });

  // Keyboard activation of elements that are clickable but not natively
  // focusable controls (role="link" cards): Enter triggers the same htmx "click"
  // the mouse would — a div gets no native click from Enter. The element carries
  // hx-get/hx-target itself. `defaultPrevented` is honoured here (unlike the
  // click handler) because this one synthesises an event: if an inner control
  // already handled the Enter, firing the card's request too would be wrong.
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || event.defaultPrevented) return;
    var el = closestFrom(event, "[data-keyboard-activate]");
    if (el && window.htmx) {
      window.htmx.trigger(el, "click");
    }
  });

  document.addEventListener("click", function (event) {
    var el = closestFrom(event, "[data-action]");
    if (!el) return;
    var action = CLICK_ACTIONS[el.getAttribute("data-action")];
    if (action) action(el);
  });
})();
