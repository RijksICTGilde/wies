"use strict";

/**
 * Lets the error of a control that is no form input reach the screen reader.
 * nldd-form-field hands its validation list to the input as an accessible
 * description, but the client picker's control is a button the field does not
 * recognise, so its list points at the button with `for` and nobody describes
 * the button. This does, with "Fout:" in front because a button, unlike a
 * field, does not say "ongeldig" itself.
 *
 * TODO: delete this file once nldd-form-field describes the control that an
 * nldd-validation-list names in `for`. Reported to NLDD; not in 0.8.92. Check:
 * submit the opdracht form with only a name, and VoiceOver should read "Fout:
 * Voeg minimaal 1 opdrachtgever toe." on the picker button without this script.
 */

var BORROWED = "nldd-validation-list[for]";

function describe(list) {
  var control = document.getElementById(list.getAttribute("for"));
  if (!control || !control.hasAttribute("invalid")) return;
  var ids = (control.getAttribute("unmet") || "").split(/\s+/);
  var words = [];
  for (var i = 0; i < ids.length; i++) {
    var item = ids[i] && document.getElementById(ids[i]);
    if (item) words.push(item.textContent.trim());
  }
  if (!words.length) return;
  // Lit renders the shadow root a frame after the element connects.
  var ready = control.updateComplete || Promise.resolve();
  ready.then(function () {
    var target = control.shadowRoot
      ? control.shadowRoot.querySelector("button, a, input")
      : null;
    (target || control).setAttribute(
      "aria-description",
      "Fout: " + words.join(". "),
    );
  });
}

function describeAll(root) {
  if (!root || typeof root.querySelectorAll !== "function") return;
  var lists = root.querySelectorAll(BORROWED);
  for (var i = 0; i < lists.length; i++) describe(lists[i]);
}

document.addEventListener("htmx:afterSettle", function (event) {
  describeAll(event.target);
});
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    describeAll(document);
  });
} else {
  describeAll(document);
}
