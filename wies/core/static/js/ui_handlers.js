// Delegated UI handlers. The CSP is script-src 'self', so inline handlers are
// blocked silently and bindings are declared as data-attributes and resolved
// here; test_templates_no_inline_js.py guards that.
//
// Never skips on defaultPrevented: htmx cancels the native event on every
// element it drives, which would drop actions on elements carrying both.

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
    var el = window.wiesClosestInPath(event, "nldd-notification");
    if (el) el.remove();
  });
})();
