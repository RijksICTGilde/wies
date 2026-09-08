// Shows the closing-reason field only while the status is "Gesloten".
//
// The reason explains a status, so on anything else it is a question nobody is
// answering. Server-side rendering cannot decide this: the status is picked in
// the same form, so the field has to follow the dropdown as it changes.
(function () {
  "use strict";

  const CLOSED = "GESLOTEN";
  const FIELD = "[data-closing-reason-field]";

  function statusOf(form) {
    const control = form.querySelector("[name=status]");
    return control ? control.value : "";
  }

  function sync(form) {
    const field = form.querySelector(FIELD);
    if (!field) return;
    const closed = statusOf(form) === CLOSED;
    field.hidden = !closed;
    // Leaving a value behind would save a reason for work that is running
    // again, so clearing it is part of hiding it.
    if (!closed) {
      const input = field.querySelector("[name=closing_reason]");
      if (input && input.value) input.value = "";
    }
  }

  function formsWithField(root) {
    if (!root || !root.querySelectorAll) return [];
    return [...root.querySelectorAll(FIELD)]
      .map((field) => field.closest("form"))
      .filter(Boolean);
  }

  function scan(root) {
    for (const form of formsWithField(root)) sync(form);
  }

  // The status control is an nldd combo box, so its change event crosses a
  // shadow boundary; listen on the document and find the form from the path.
  document.addEventListener("change", (e) => {
    const form = e.target instanceof Element ? e.target.closest("form") : null;
    if (form) sync(form);
  });

  document.body?.addEventListener("htmx:afterSettle", (e) =>
    scan(e.detail?.target || document),
  );

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => scan(document));
  } else {
    scan(document);
  }
})();
