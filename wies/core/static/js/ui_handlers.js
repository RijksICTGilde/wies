// Delegated UI handlers, registered once on `document`.
//
// Bindings are declared in the markup as data-attributes (`data-action`,
// `data-confirm`) and resolved here, so the element still says what it does
// without needing an inline on*= attribute — those would force 'unsafe-inline'
// back into script-src. Delegation also keeps the bindings alive across HTMX
// swaps (the event blocks re-render) without re-binding.
//
// Adding a UI interaction: give the element data-action="<name>" and add the
// matching entry to CLICK_ACTIONS below. Never reach for on*= or inline
// <script>; the CSP blocks those silently and test_templates_no_inline_js.py
// fails the build.
//
// The click listener sits on `document`, so htmx's own element-level listeners
// have already run by the time it fires. It therefore never calls preventDefault
// or skips on `defaultPrevented` — htmx cancels the native event on every element
// it drives, so treating "already cancelled" as "already handled" would silently
// drop actions on any element that carries both hx-* and data-action.

(function () {
  var CLICK_ACTIONS = {
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

  document.addEventListener("click", function (event) {
    var el = closestFrom(event, "[data-action]");
    if (!el) return;
    var action = CLICK_ACTIONS[el.getAttribute("data-action")];
    if (action) action(el);
  });
})();
