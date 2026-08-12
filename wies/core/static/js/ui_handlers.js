// Delegated UI handlers, registered once on `document`. This file exists
// because the CSP is script-src 'self': inline <script> and on*= attributes are
// blocked silently, so bindings are declared in the markup as data-attributes
// (`data-action`, `data-confirm`) and resolved here. Delegation also keeps them
// alive across HTMX swaps. To add an interaction, give the element
// data-action="<name>" and add an entry to CLICK_ACTIONS below;
// test_templates_no_inline_js.py fails the build on inline JS.
//
// The click listener sits on `document`, so htmx's element-level listeners have
// already run. It never skips on `defaultPrevented`: htmx cancels the native
// event on every element it drives, which would silently drop actions on
// elements carrying both hx-* and data-action.

(function () {
  var CLICK_ACTIONS = {
    // history.back() does nothing when the page was opened directly (pasted
    // URL, bookmark), so fall back to the home page.
    "history-back": function () {
      if (window.history.length > 1) window.history.back();
      else window.location.assign("/");
    },
  };

  // event.target is not an Element for events dispatched at document/window, so
  // route every lookup through this.
  function closestFrom(event, selector) {
    var target = event.target;
    return target && target.closest ? target.closest(selector) : null;
  }

  // <form data-confirm="..."> cancels the submit if the user declines. Plain
  // forms only: htmx issues its request from its own submit listener, which runs
  // before this one. Use hx-confirm on htmx-driven forms.
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

  // nldd-notification announces its dismissal but does not remove itself: the
  // consumer decides. We do not keep them around.
  document.addEventListener("dismiss", function (event) {
    var el = event.composedPath().find(function (node) {
      return (
        node instanceof Element &&
        node.tagName &&
        node.tagName.toLowerCase() === "nldd-notification"
      );
    });
    if (el) el.remove();
  });
})();
