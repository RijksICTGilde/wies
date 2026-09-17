"use strict";

/**
 * Lets the error under a rejected field reach the screen reader.
 *
 * nldd-form-field wires a field's errors the standard way: the input gets
 * aria-describedby="<id of the error text>". But that input sits in the
 * component's shadow root and the error text in the page, and an id reference
 * cannot cross that boundary: the browser resolves it to nothing, so VoiceOver
 * says "ongeldige invoer" and not why. Element reflection
 * (ariaDescribedByElements) may point across it; where the browser lacks
 * that, aria-description carries the same words as a plain string.
 *
 * Runs once the page is loaded and after every htmx settle, on the fields
 * wire_field_errors() marked with `invalid` and `error-message`. A rejected
 * element that is no control itself, like the <div> the client picker marks,
 * lends the description to the first control inside it.
 */

var REJECTED = "[invalid][error-message]";
var CONTROL = "input, textarea, select, button";
var LIGHT_CONTROL = "nldd-button, button, input:not([type=hidden]), select, textarea";

// The element a screen reader reads when this one is focused: the control in
// its shadow root, else the first control inside it (borrowed: that control is
// not the invalid thing, so its description has to say it is an error).
function controlIn(host) {
  var shadow = host.shadowRoot ? host.shadowRoot.querySelector(CONTROL) : null;
  if (shadow) return { control: shadow, borrowed: false };
  var light = host.querySelector(LIGHT_CONTROL);
  if (!light) return null;
  return {
    control: light.shadowRoot
      ? light.shadowRoot.querySelector(CONTROL)
      : light,
    borrowed: true,
  };
}

function wording(errors) {
  return errors
    .map(function (el) {
      return el.textContent.trim();
    })
    .join(". ");
}

function describe(host) {
  var ids = (host.getAttribute("error-message") || "").split(/\s+/);
  var errors = [];
  for (var i = 0; i < ids.length; i++) {
    var el = ids[i] && document.getElementById(ids[i]);
    if (el) errors.push(el);
  }
  if (!errors.length) return;
  // Lit renders the shadow root a frame after the element connects; until
  // then there is no input to describe.
  var ready =
    host.updateComplete && typeof host.updateComplete.then === "function"
      ? host.updateComplete
      : Promise.resolve();
  ready.then(function () {
    var found = controlIn(host);
    if (!found || !found.control) return;
    var control = found.control;
    // A field says "ongeldig" itself through aria-invalid; a borrowed button
    // does not, so the words have to. That rules out element reflection there.
    if (found.borrowed) {
      control.setAttribute("aria-description", "Fout: " + wording(errors));
      return;
    }
    if ("ariaDescribedByElements" in control) {
      control.ariaDescribedByElements = errors;
      return;
    }
    control.setAttribute("aria-description", wording(errors));
  });
}

function describeAll(root) {
  if (!root || typeof root.querySelectorAll !== "function") return;
  var hosts = root.querySelectorAll(REJECTED);
  for (var i = 0; i < hosts.length; i++) describe(hosts[i]);
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
