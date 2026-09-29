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

  // Long free text (#576): two spans swapped via hidden. The toggle is an
  // nldd-button, so its text, icon and state are set via attributes.
  function toggleLongText(toggle) {
    var wrapper = toggle.parentElement;
    var truncated = wrapper && wrapper.querySelector(".inline-edit-long-text__truncated");
    var full = wrapper && wrapper.querySelector(".inline-edit-long-text__full");
    if (!truncated || !full) return;
    var expanded = full.hidden === false;
    truncated.hidden = !expanded;
    full.hidden = expanded;
    var text = expanded ? "Toon meer" : "Toon minder";
    toggle.setAttribute("text", text);
    // A card toggle names its subject ("Toon meer over de rol ..."); the verb
    // in that name follows the state too.
    var label = toggle.getAttribute("accessible-label");
    if (label) toggle.setAttribute("accessible-label", label.replace(/^Toon (meer|minder)/, text));
    // nldd-button forwards `expanded` as aria-expanded on its inner button.
    toggle.toggleAttribute("expanded", !expanded);
    // The role-description toggle has no icon; only flip one that is there.
    if (toggle.hasAttribute("start-icon")) {
      toggle.setAttribute("start-icon", expanded ? "chevron-down" : "chevron-up");
    }
  }

  // An opdracht card on a colleague panel or profile: a click anywhere on the
  // card opens or closes it; the chevron button carries the state.
  function toggleCard(el) {
    var card = el.closest("nldd-card");
    var more = card && card.querySelector(".wies-card__more");
    if (!more) return;
    var open = more.hidden;
    more.hidden = !open;
    var preview = card.querySelector(".wies-card__preview");
    if (preview) preview.hidden = open;
    var toggle = card.querySelector(".wies-card__toggle");
    if (!toggle) return;
    toggle.toggleAttribute("expanded", open);
    toggle.setAttribute("icon", open ? "chevron-up" : "chevron-down");
    var label = toggle.getAttribute("text") || "";
    toggle.setAttribute("text", label.replace(/^(Meer|Minder) over/, open ? "Minder over" : "Meer over"));
  }

  var CLICK_ACTIONS = {
    "history-back": goBack,
    "toggle-long-text": toggleLongText,
    "toggle-card": toggleCard,
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

  var INTERACTIVE = "a, button, [href], [hx-get], [hx-post], [data-action]";

  document.addEventListener("click", function (event) {
    var el = closestFrom(event, "[data-action]");
    if (!el) return;
    // A whole card can carry an action; a link or button inside it is its
    // own click and must not also trigger the card's.
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
