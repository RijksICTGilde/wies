"use strict";

/**
 * Says what an htmx swap changed, for someone who cannot see it change: the
 * result count, a notification, the errors of a rejected form. A live region
 * only announces text that changes inside a region that was already there, so
 * base.html holds one empty region and this module fills it. DOM access goes
 * through the injected document so the decisions are testable without a browser.
 */

// Templates put the count on the list they render ("12 gebruikers").
var ANNOUNCE = "[data-announce]";
// A rejected control names the ids of its nldd-validation-items in `unmet`.
var REJECTED = "[invalid][unmet]";
// Announced when it enters the document: the server's flash block, a script's
// toast, or the region every nldd-notification moves itself into a moment
// later. That move adds it a second time, which the repeat window swallows.
var NOTIFICATION = "nldd-notification[text]";
var NOTIFICATION_REGION = "nldd-notification-region";
var SHEET_REGION = "[data-wies-live]";
// Not the ones inside a role="alert": those are read out by that already.

// A request settles once per swapped element, and a list can arrive both in
// the target and out of band: the same text within this window is one event.
var REPEAT_WINDOW = 1000;

// Between emptying the region and filling it. Long enough that a focus move
// in the same swap (focus_restore.js sends the user to the rejected field) is
// announced first and the message follows, instead of the two talking over
// each other.
var FILL_DELAY = 300;

// After a full page load a live region is no use: measured with VoiceOver in
// Chrome, a change to one is never spoken then, the page announcement wins.
// What has focus is always spoken, so the message gets focus instead, as the
// GOV.UK notification banner does. It sits first in the body, so the next Tab
// lands on the skip link as on any fresh page.
var LOAD_DELAY = 1000;

function LiveRegion(doc, options) {
  this.doc = doc;
  this.setTimeout =
    (options && options.setTimeout) ||
    function (fn, ms) {
      return setTimeout(fn, ms);
    };
  this.now =
    (options && options.now) ||
    function () {
      return Date.now();
    };
  this.MutationObserver =
    (options && options.MutationObserver) ||
    (typeof MutationObserver === "function" ? MutationObserver : null);
  this.lastText = "";
  this.lastAt = 0;
  // Texts of the notifications that came with the page: handleLoad announces
  // those, so the watcher leaves them alone when they move into the region.
  this.loadTexts = [];
}

// On a narrow viewport the side panel is a modal dialog, and a modal makes
// everything outside it inert: for a screen reader that content is not there.
// Slotted content belongs to the dialog, so a modal sheet gets its own region.
LiveRegion.prototype.modalSheet = function () {
  var sheets = this.doc.querySelectorAll("nldd-sheet");
  for (var i = 0; i < sheets.length; i++) {
    var root = sheets[i].shadowRoot;
    var dialog =
      root && root.querySelector ? root.querySelector("dialog") : null;
    if (
      dialog &&
      typeof dialog.matches === "function" &&
      dialog.matches(":modal")
    )
      return sheets[i];
  }
  return null;
};

// Ahead of time: a region only counts once it exists before its text changes.
LiveRegion.prototype.prepareSheets = function () {
  var sheets = this.doc.querySelectorAll("nldd-sheet");
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].querySelector(SHEET_REGION)) continue;
    var region = this.doc.createElement("div");
    region.className = "wies-visually-hidden";
    region.setAttribute("role", "status");
    region.setAttribute("data-wies-live", "");
    sheets[i].appendChild(region);
  }
};

// NLDD moves its notification box into the topmost modal overlay, but it only
// starts listening for overlays opening once the first notification has
// joined, so a sheet that was already open is unknown to it and the box stays
// on the body, behind the backdrop and inert. Sending the `open` event that
// sheet would have sent had it opened later puts it on NLDD's list, and NLDD
// relocates the box itself, carrying the notifications along.
LiveRegion.prototype.nudgeNotifications = function () {
  var sheet = this.modalSheet();
  var region = this.doc.getElementById(NOTIFICATION_REGION);
  if (!sheet || !region || sheet.contains(region)) return;
  if (typeof sheet.dispatchEvent !== "function" || typeof Event !== "function")
    return;
  sheet.dispatchEvent(new Event("open", { bubbles: true }));
};

LiveRegion.prototype.region = function () {
  var sheet = this.modalSheet();
  var inSheet = sheet && sheet.querySelector(SHEET_REGION);
  return inSheet || this.doc.getElementById("wies-live");
};

function texts(container, selector, read) {
  var found = [];
  if (typeof container.matches === "function" && container.matches(selector))
    found.push(container);
  var inner = container.querySelectorAll(selector);
  for (var i = 0; i < inner.length; i++) found.push(inner[i]);
  var out = [];
  for (var j = 0; j < found.length; j++) {
    var text = (read(found[j]) || "").trim();
    if (text) out.push(text);
  }
  return out;
}

// The messages the rejected controls in a fragment point at, each once: the
// client picker's wrapper and its button name the same ids.
LiveRegion.prototype.errorTexts = function (container) {
  var self = this;
  var seen = {};
  var out = [];
  texts(container, REJECTED, function (el) {
    var ids = (el.getAttribute("unmet") || "").split(/\s+/);
    for (var i = 0; i < ids.length; i++) {
      if (!ids[i] || seen[ids[i]]) continue;
      seen[ids[i]] = true;
      var item = self.doc.getElementById(ids[i]);
      var text = item && item.textContent ? item.textContent.trim() : "";
      if (text) out.push(text);
    }
    return "";
  });
  return out;
};

// The errors of a rejected form as one sentence, so the user hears at once
// that the save failed and why. Focus moves to the first field separately.
function errorSentence(errors) {
  if (!errors.length) return "";
  var head =
    errors.length === 1
      ? "Het formulier heeft 1 fout: "
      : "Het formulier heeft " + errors.length + " fouten: ";
  return head + errors.join(". ");
}

// What a settled fragment asks to be read out, in the order it reads on screen.
LiveRegion.prototype.messagesIn = function (container) {
  if (!container || typeof container.querySelectorAll !== "function") return [];
  var out = texts(container, ANNOUNCE, function (el) {
    return el.getAttribute("data-announce");
  });
  var sentence = errorSentence(this.errorTexts(container));
  if (sentence) out.push(sentence);
  return out;
};

LiveRegion.prototype.announce = function (text) {
  var region = this.region();
  if (!region || !text) return false;
  var at = this.now();
  if (text === this.lastText && at - this.lastAt < REPEAT_WINDOW) return false;
  this.lastText = text;
  this.lastAt = at;
  // Empty first, then fill a tick later: the same words twice in a row are
  // otherwise not a change, and the user would not hear the second result.
  region.textContent = "";
  this.setTimeout(function () {
    region.textContent = text;
  }, FILL_DELAY);
  return true;
};

LiveRegion.prototype.handleSettle = function (container) {
  var messages = this.messagesIn(container);
  if (!messages.length) return false;
  return this.announce(messages.join(". "));
};

// Nested ones included: the flash block is a wrapper with notifications inside.
function notificationTexts(nodes) {
  var out = [];
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i];
    if (!node || typeof node.getAttribute !== "function") continue;
    var found = [];
    if (typeof node.matches === "function" && node.matches(NOTIFICATION))
      found.push(node);
    if (typeof node.querySelectorAll === "function") {
      var inner = node.querySelectorAll(NOTIFICATION);
      for (var k = 0; k < inner.length; k++) found.push(inner[k]);
    }
    for (var j = 0; j < found.length; j++) {
      var text = (found[j].getAttribute("text") || "").trim();
      // Appended and then moved into the region within one batch: once.
      if (text && out.indexOf(text) === -1) out.push(text);
    }
  }
  return out;
}

LiveRegion.prototype.handleNotifications = function (nodes) {
  var self = this;
  var messages = notificationTexts(nodes).filter(function (text) {
    return self.loadTexts.indexOf(text) === -1;
  });
  if (!messages.length) return;
  this.nudgeNotifications();
  this.announce(messages.join(". "));
};

LiveRegion.prototype.watchNotifications = function () {
  var self = this;
  if (!this.MutationObserver || !this.doc.body) return;
  new this.MutationObserver(function (records) {
    var added = [];
    for (var i = 0; i < records.length; i++) {
      var nodes = records[i].addedNodes;
      for (var j = 0; j < nodes.length; j++) added.push(nodes[j]);
    }
    self.handleNotifications(added);
  }).observe(this.doc.body, { childList: true, subtree: true });
};

// A notification that came with the page, after a redirect: see LOAD_DELAY.
LiveRegion.prototype.handleLoad = function () {
  var self = this;
  var messages = notificationTexts(this.doc.querySelectorAll(NOTIFICATION));
  if (!messages.length) return;
  this.loadTexts = messages;
  this.setTimeout(function () {
    self.loadTexts = [];
    var spoken = self.doc.getElementById("wies-alert");
    if (!spoken) return;
    spoken.textContent = messages.join(". ");
    spoken.setAttribute("tabindex", "-1");
    if (typeof spoken.focus === "function")
      spoken.focus({ preventScroll: true });
  }, LOAD_DELAY);
};

LiveRegion.prototype.bind = function () {
  var self = this;
  // Fires on each element that was settled in, the out-of-band ones included;
  // detail.target would be the old element after an outerHTML swap.
  this.doc.addEventListener("htmx:afterSettle", function (event) {
    self.prepareSheets();
    self.handleSettle(event.target);
  });
  function onLoad() {
    self.prepareSheets();
    self.watchNotifications();
    self.handleLoad();
  }
  if (this.doc.readyState === "loading") {
    this.doc.addEventListener("DOMContentLoaded", onLoad);
  } else {
    onLoad();
  }
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = LiveRegion;
} else {
  window.LiveRegion = LiveRegion;
  new LiveRegion(document).bind();
}
