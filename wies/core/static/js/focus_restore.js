"use strict";

/**
 * Gives focus a destination when an htmx swap drops it.
 *
 * A swap that replaces the focused element leaves focus on <body>, so the next
 * Tab starts at the top of the page. htmx restores focus itself, but only when
 * an element with the same id survives the swap, which covers neither a form
 * replaced by its read view nor a panel that is fetched again.
 *
 * DOM access goes through the injected document, so the decisions are testable
 * without a browser; the wiring at the bottom binds an instance to htmx.
 */

// In order of reliability. An id is unique; a URL identifies the action, which
// works just as well here and asks nothing of the templates. A reference to the
// node itself is worthless: it is detached once the panel is fetched again.
var IDENTIFYING_ATTRIBUTES = ["id", "hx-get", "hx-post", "href"];

// What a user can operate. The custom elements are listed because the NLDD
// components put their real control in a shadow root: `nldd-button` matches no
// standard selector but is a tab stop.
//
// Only components that accept focus(), through delegatesFocus or their own
// focus() override. nldd-checkbox, nldd-radio-button, the -field variants and
// nldd-segmented-control have neither, so focus() on them silently does
// nothing. A selector that matches but does not focus is worse than no match:
// it crowds out an element further along that would have taken it.
//
// nldd-dropdown is absent on purpose: it wraps a real <select> in light DOM,
// which "select" already matches. The host precedes it in document order and
// would steal that match.
//
// The tab bar uses a roving tabindex, so only the selected tab is the way in.
// That tabindex sits in the shadow root where the selector cannot see it, hence
// [selected].
var FOCUSABLE = [
  "a[href]",
  "button",
  "input:not([type=hidden])",
  "select",
  "textarea",
  "[tabindex]:not([tabindex='-1'])",
  "nldd-button",
  "nldd-icon-button",
  "nldd-link",
  "nldd-list-item[href]",
  "nldd-search-field",
  "nldd-text-field",
  "nldd-multi-line-text-field",
  "nldd-date-field",
  "nldd-number-field",
  "nldd-password-field",
  "nldd-combo-box",
  "nldd-token-field",
  "nldd-switch",
  "nldd-tab-bar-item[selected]",
  "nldd-menu-bar-item",
].join(",");

// A save that bounces back with HX-Location produces three swaps: the button
// that opened the form, the submit, and htmx fetching the panel again. That
// last one has no source element, so the button we came from sits two steps
// back. Five leaves room for one more level; deeper than that an entry is more
// likely to be stale than useful.
var MAX_DEPTH = 5;

function FocusRestore(doc, options) {
  this.doc = doc;
  this.maxDepth = (options && options.maxDepth) || MAX_DEPTH;
  // Newest first. Each entry describes an element instead of pointing at one,
  // so it survives a fresh render.
  this.trail = [];
  // Clicking is a pointing action: that user knows where they are and needs no
  // destination. Only a keyboard user loses their place when focus drops.
  this.lastInput = "keyboard";
}

FocusRestore.prototype.describe = function (element) {
  if (!element || typeof element.getAttribute !== "function") return null;
  for (var i = 0; i < IDENTIFYING_ATTRIBUTES.length; i++) {
    var attribute = IDENTIFYING_ATTRIBUTES[i];
    var value = element.getAttribute(attribute);
    if (value) return { attribute: attribute, value: value };
  }
  return null;
};

FocusRestore.prototype.remember = function (element) {
  var descriptor = this.describe(element);
  if (!descriptor) return;
  this.trail = [descriptor].concat(this.trail).slice(0, this.maxDepth);
};

FocusRestore.prototype.isVisible = function (element) {
  return typeof element.checkVisibility === "function"
    ? element.checkVisibility()
    : true;
};

// The visible candidate wins: an action is often in the DOM twice, as a button
// and as a hidden item in the overflow menu beside it.
FocusRestore.prototype.resolve = function (descriptor) {
  var matches = Array.prototype.slice.call(
    this.doc.querySelectorAll("[" + descriptor.attribute + "]"),
  );
  for (var i = 0; i < matches.length; i++) {
    if (matches[i].getAttribute(descriptor.attribute) !== descriptor.value)
      continue;
    if (this.isVisible(matches[i])) return matches[i];
  }
  return null;
};

// focus() on a custom element without delegatesFocus does nothing and does not
// report that, so check whether it took instead of assuming.
FocusRestore.prototype.focusTook = function (element) {
  var active = this.doc.activeElement;
  return (
    active === element ||
    (typeof element.contains === "function" && element.contains(active))
  );
};

// Keep going until one takes. Stopping at the first match would leave focus on
// <body>, which is what this module exists to prevent.
FocusRestore.prototype.focusFirst = function (elements, options) {
  var preventScroll = !options || options.preventScroll !== false;
  var list = Array.prototype.slice.call(elements);
  for (var i = 0; i < list.length; i++) {
    var element = list[i];
    if (!this.isVisible(element) || typeof element.focus !== "function")
      continue;
    element.focus({ preventScroll: preventScroll });
    if (this.focusTook(element)) return true;
  }
  return false;
};

FocusRestore.prototype.focusFromTrail = function () {
  for (var i = 0; i < this.trail.length; i++) {
    var element = this.resolve(this.trail[i]);
    if (!element || typeof element.focus !== "function") continue;
    element.focus({ preventScroll: true });
    if (!this.focusTook(element)) continue;
    // Everything up to and including this step is dealt with; anything newer
    // belongs to a level we just came back from.
    this.trail = this.trail.slice(i + 1);
    return true;
  }
  return false;
};

FocusRestore.prototype.handleSettle = function (container) {
  if (!container || typeof container.querySelector !== "function") return;

  // A rejected form comes back with the error in it, and then the first
  // operable place is not where the user has to be. The one step that also
  // applies to a mouse user and regardless of where focus is, because what
  // changed is where the user belongs. Without preventScroll, or you cannot see
  // where you were sent.
  //
  // `invalid` is the convention of wire_field_errors(): every widget puts it on
  // the element nldd-form-field._findInput() returns. The error text carries it
  // too but is not an input.
  var invalid = container.querySelectorAll(
    "[invalid]:not(nldd-form-field-error-text)",
  );
  if (invalid.length && this.focusFirst(invalid, { preventScroll: false }))
    return;

  if (this.lastInput === "mouse") return;

  // Focus survived the swap, so nothing was lost. Filtering refreshes the list
  // this way while the caret stays in the field. Note that searching does not
  // land here: commitSearch() blurs the field itself, so focus is on <body> and
  // a keyboard user is put on the first result below.
  var active = this.doc.activeElement;
  if (active && active !== this.doc.body && active !== this.doc.documentElement)
    return;

  // The server knows better, and htmx has already focused it.
  if (
    container.matches("[autofocus]") ||
    container.querySelector("[autofocus]")
  )
    return;

  if (this.focusFromTrail()) return;

  // The first operable element inside the new content, explicitly not the
  // container itself. That container is a component (`nldd-page`, `nldd-sheet`)
  // and so a shadow host, where the host's tabindex decides whether its content
  // takes part in the tab order at all, so making it focusable costs more than
  // it gives. If nothing takes, leaving focus on <body> beats breaking the tab
  // order.
  this.focusFirst(container.querySelectorAll(FOCUSABLE));
};

FocusRestore.prototype.bind = function () {
  var self = this;
  this.doc.addEventListener(
    "keydown",
    function () {
      self.lastInput = "keyboard";
    },
    true,
  );
  this.doc.addEventListener(
    "pointerdown",
    function () {
      self.lastInput = "mouse";
    },
    true,
  );
  this.doc.addEventListener("htmx:beforeRequest", function (event) {
    self.remember(event.detail.elt);
  });
  // Going back in browser history is a different context; what we remembered
  // is not about that one.
  this.doc.addEventListener("htmx:historyRestore", function () {
    self.trail = [];
  });
  this.doc.addEventListener("htmx:afterSettle", function (event) {
    self.handleSettle(event.detail.target);
  });
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = FocusRestore;
} else {
  window.FocusRestore = FocusRestore;
  new FocusRestore(document).bind();
}
