// Delegated UI handlers: the CSP blocks inline handlers. Never skips on
// defaultPrevented — htmx cancels the native event on everything it drives.

(function () {
  // Both signals are needed. A referrer alone does not distinguish "previous
  // page in this tab" from "opener in another tab": ctrl- or middle-clicking an
  // internal link (the footer's Veelgestelde vragen, say) gives a same-origin
  // referrer in a tab with no history, and back() then does nothing at all. And
  // history.length alone does not help either, since a page opened fresh still
  // reports 2. Together they cover all three cases.
  function goBack() {
    var from = document.referrer;
    var sameOrigin = from && new URL(from).origin === window.location.origin;
    if (sameOrigin && window.history.length > 1) window.history.back();
    else window.location.assign("/");
  }

  var CLICK_ACTIONS = {
    "history-back": goBack,
  };

  function closestFrom(event, selector) {
    var target = event.target;
    return target && target.closest ? target.closest(selector) : null;
  }

  // Plain forms only: htmx fires its request from its own submit listener,
  // which runs before this one. Use hx-confirm there.
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

  // nldd-top-navigation-bar fires back-click only when it has no back-href; with
  // one it navigates itself. The information pages are reached from the footer of
  // any page, so a fixed href would send you somewhere you have not been.
  document.addEventListener("back-click", goBack);

  // nldd-notification announces its dismissal but does not remove itself.
  document.addEventListener("dismiss", function (event) {
    var el = window.wiesClosestInPath(event, "nldd-notification");
    if (el) el.remove();
  });
})();
