// Applies the Bezetting filters (merk + label categories) when a filter
// dropdown closes — the user can tick several boxes with the popover open, and
// the page reloads once when they click away. Submits only if something actually
// changed, so merely opening and closing a dropdown does not reload.
//
// CSP-safe: external file, delegated events. The nldd-checkbox-fields live in
// nldd-popover panels; their "change" bubbles to the form, and the popover's
// "close" event (bubbles + composed) reaches the document.

(function () {
  "use strict";

  var form = document.querySelector("[data-bezetting-filter]");
  if (!form) return;

  // JS is available: the manual "Filteren" button is redundant.
  var submit = form.querySelector(".bezetting-filter__submit");
  if (submit) submit.hidden = true;

  var dirty = false;

  // A checkbox changed inside a still-open dropdown.
  form.addEventListener("change", function () {
    dirty = true;
  });

  // The DS popover closed (outside click, Escape, or opening another). Apply the
  // pending selection, once, only if it changed.
  document.addEventListener("close", function (event) {
    var popover = event.target;
    if (!popover || popover.localName !== "nldd-popover") return;
    if (!form.contains(popover)) return;
    if (!dirty) return;
    dirty = false;
    // form.submit() (not requestSubmit): the only submit button is hidden, so it
    // is not a valid submitter; a plain GET navigation is all we need here.
    form.submit();
  });
})();
