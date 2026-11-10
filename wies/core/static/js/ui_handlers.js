// Delegated UI handlers: the CSP blocks inline handlers. Never skips on
// defaultPrevented — htmx cancels the native event on everything it drives.

(function () {
  // Under Node (js_tests) there is no document to bind to: export the toggles,
  // which are pure DOM manipulation, and skip the listeners. They are the part
  // that silently stopped matching its markup once (#693).
  var testing = typeof module !== "undefined" && module.exports;

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

  // Long free text (#576): rendered Markdown in one block, collapsed by a
  // class on the wrapper. The toggle is an nldd-button, so its text, icon and
  // state are set via attributes.
  function toggleLongText(toggle) {
    var wrapper = toggle.closest(".wies-long-text");
    if (!wrapper) return;
    var expanded = !wrapper.classList.contains("wies-long-text--collapsed");
    wrapper.classList.toggle("wies-long-text--collapsed", expanded);
    // Collapsed, no gap between blocks, so the cut falls between two lines.
    var body = wrapper.querySelector("nldd-rich-text");
    if (body) body.setAttribute("spacing", expanded ? "flat" : "tight");
    toggle.setAttribute("text", expanded ? "Toon meer" : "Toon minder");
    toggle.setAttribute("start-icon", expanded ? "chevron-down" : "chevron-up");
    // nldd-button forwards `expanded` as aria-expanded on its inner button.
    toggle.toggleAttribute("expanded", !expanded);
  }

  // "Toon meer" on an opdracht entry in a colleague's cv list unfolds the role
  // description. Nothing around it is clickable, so the click needs no guard.
  function toggleCard(el) {
    var entry = el.closest(".wies-cv__item");
    var more = entry && entry.querySelector(".wies-cv__more");
    if (!more) return;
    var open = more.hidden;
    more.hidden = !open;
    var preview = entry.querySelector(".wies-cv__preview");
    if (preview) preview.hidden = open;
    var text = open ? "Toon minder" : "Toon meer";
    el.toggleAttribute("expanded", open);
    el.setAttribute("start-icon", open ? "chevron-up" : "chevron-down");
    el.setAttribute("text", text);
    // The accessible name has to start with the visible text, or a voice
    // command saying what is on screen does not reach the button.
    var object = el.getAttribute("data-toggle-object");
    if (object) el.setAttribute("accessible-label", text + " " + object);
  }

  var CLICK_ACTIONS = {
    "history-back": goBack,
    "toggle-long-text": toggleLongText,
    "toggle-card": toggleCard,
  };

  if (testing) {
    module.exports = { toggleLongText: toggleLongText, toggleCard: toggleCard };
    return;
  }

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

  var INTERACTIVE = "a, button, [href], [hx-get], [hx-post], [data-action]";

  document.addEventListener("click", function (event) {
    var el = closestFrom(event, "[data-action]");
    if (!el) return;
    // An element carrying an action may wrap a link or button; that inner
    // click is its own and must not also trigger the outer action.
    var inner = closestFrom(event, INTERACTIVE);
    if (inner && inner !== el && el.contains(inner)) return;
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
