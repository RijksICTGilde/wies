"use strict";

/**
 * Says what an htmx swap changed, for someone who cannot see it change.
 *
 * A filter refreshes the list in place, a save drops a notification in the
 * corner, a rejected form paints its errors under the fields. Sighted users see
 * all of that; a screen reader stays silent, because the parts arrive complete
 * and a live region only announces text that changes inside a region that was
 * already there. So base.html holds one empty region, and this module copies
 * into it whatever the swapped-in content asks to be read out, and every
 * notification that lands in the NLDD notification region, whether the server
 * sent it or a script made it.
 *
 * One complication: on a narrow viewport the side panel opens as a modal
 * dialog, and a modal makes everything outside it inert. For a screen reader
 * that content is not there, and the notification in the corner is painted
 * behind the backdrop. Slotted content, though, belongs to the dialog. So while
 * a sheet is modal, the region that is read out and the notification region
 * both live inside the sheet.
 *
 * DOM access goes through the injected document so the decisions are testable
 * without a browser; the wiring at the bottom binds an instance to htmx.
 */

// What a fragment asks to be read out. Templates put the count on the list they
// render ("12 gebruikers", "Geen opdrachten gevonden"); error texts carry their
// own words.
var ANNOUNCE = "[data-announce]";
// A notification is announced when it enters the document, wherever that is:
// the server's flash block, a script's toast, or the region every
// nldd-notification moves itself into a moment later. That move adds it a
// second time, which the repeat window swallows.
var NOTIFICATION = "nldd-notification[text]";
var NOTIFICATION_REGION = "nldd-notification-region";
var SHEET_REGION = "[data-wies-live]";
// Not the ones inside a role="alert": those are read out by that already.
var ERROR_TEXT = "nldd-form-field-error-text";
var ALERT = "[role='alert']";

// The same text within this window is one event heard from several sides: a
// request settles once per swapped element, and a list can arrive both inside
// the target and out of band.
var REPEAT_WINDOW = 1000;

// Between emptying the region and filling it. Long enough that a focus move
// in the same swap (focus_restore.js sends the user to the rejected field) is
// announced first and the message follows, instead of the two talking over
// each other.
var FILL_DELAY = 300;

// After a full page load the flash message is already in the page, and a live
// region is no use: measured with VoiceOver in Chrome, a change to one, polite
// or assertive, 1.5 s after the load is never spoken, the page announcement
// wins. What has focus is always spoken, so the message gets focus instead,
// the way the GOV.UK notification banner does on page load. It sits at the top
// of the body, so the next Tab lands on the skip link as on any fresh page.
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

// The sheet whose dialog is modal right now, if any. The dialog sits in the
// component's shadow root; :modal is the one thing about it we need to know.
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

// Every sheet gets its own empty region, ahead of time: a region only counts
// once it exists before its text changes.
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

LiveRegion.prototype.region = function () {
  var sheet = this.modalSheet();
  var inSheet = sheet && sheet.querySelector(SHEET_REGION);
  return inSheet || this.doc.getElementById("wies-live");
};

// The NLDD notification region is a fixed box in the body, and a modal sheet
// paints its backdrop over it. Moving the box into the sheet is not an option:
// a notification that is disconnected on the way counts as dismissed and
// removes itself. So the box is raised into the top layer as a popover
// instead, above the dialog, and raised again for every notification, because
// a dialog opened later would stack above it. The popover user-agent styles
// that would fight the box's own (centering margin, border, canvas background)
// are neutralised inline.
LiveRegion.prototype.raiseNotifications = function () {
  var region = this.doc.getElementById(NOTIFICATION_REGION);
  if (!region || !this.modalSheet() || typeof region.showPopover !== "function")
    return;
  if (region.getAttribute("popover") !== "manual") {
    region.setAttribute("popover", "manual");
    region.style.margin = "0";
    region.style.border = "0";
    region.style.padding = "0";
    region.style.background = "transparent";
    region.style.bottom = "auto";
    region.style.overflow = "visible";
  }
  try {
    if (region.matches(":popover-open")) region.hidePopover();
    region.showPopover();
  } catch (err) {}
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
  var errors = texts(container, ERROR_TEXT, function (el) {
    if (typeof el.closest === "function" && el.closest(ALERT)) return "";
    return el.textContent;
  });
  var sentence = errorSentence(errors);
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

// The notifications among the added nodes, the ones nested in them included:
// the flash block arrives as a wrapper with the notifications inside.
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
  this.raiseNotifications();
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
