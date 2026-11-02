"use strict";

/**
 * Two gaps of nldd-date-field in a server-rendered form.
 *
 * Text that is no date: the field's value is then '', so the form posts an
 * empty date and the server stores "no end date" without a word. The field
 * knows (ownValidity), but every Wies form has `novalidate`, so nothing stops
 * the submit. This stops it for that one case and shows the field's own
 * message the way the server's errors are wired: an nldd-validation-item in
 * the nldd-form-field, named in the field's `unmet`. Everything else stays
 * with the server.
 *
 * Tab past the last button of the open calendar closes it and drops focus on
 * <body>, so the next Tab starts at the top of the page. Focus goes back to
 * the calendar button, where Escape leaves it too.
 */

(function () {
  var DATE_FIELD = "nldd-date-field";
  var ERROR_PREFIX = "date-field-error-";

  // What the field knows is wrong and its value cannot say. A hidden field
  // (an end date that is switched off) is not posted as typed, so it counts not.
  function dateProblem(field) {
    if (field.closest("[hidden]")) return null;
    var own = typeof field.ownValidity === "function" && field.ownValidity();
    return own ? own.message : null;
  }

  // `unmet` may already name the server's errors; only our own id comes and goes.
  function unmetWith(unmet, id, present) {
    var ids = (unmet || "").split(/\s+/).filter(function (part) {
      return part && part !== id;
    });
    if (present) ids.push(id);
    return ids.join(" ");
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { dateProblem: dateProblem, unmetWith: unmetWith };
    return;
  }

  var counter = 0;
  // The message shows without a focus move, which a screen reader does not
  // notice; a filter has no submit to move focus to the field.
  var liveRegion = window.LiveRegion ? new window.LiveRegion(document) : null;

  function errorId(field) {
    if (!field.dataset.dateErrorId) {
      counter += 1;
      field.dataset.dateErrorId = ERROR_PREFIX + counter;
    }
    return field.dataset.dateErrorId;
  }

  function listOf(formField) {
    var list = formField.querySelector(":scope > nldd-validation-list");
    if (!list) {
      list = document.createElement("nldd-validation-list");
      formField.appendChild(list);
    }
    return list;
  }

  // Returns whether the message is new, so it is announced once.
  function showProblem(field, message) {
    var id = errorId(field);
    var formField = field.closest("nldd-form-field");
    var item = document.getElementById(id);
    var isNew = !!message && !item;
    if (message && formField && !item) {
      item = document.createElement("nldd-validation-item");
      item.id = id;
      listOf(formField).appendChild(item);
    }
    if (item) {
      if (message) item.textContent = message;
      else item.remove();
    }
    var unmet = unmetWith(field.getAttribute("unmet"), id, !!message);
    if (unmet) field.setAttribute("unmet", unmet);
    else field.removeAttribute("unmet");
    field.toggleAttribute("invalid", !!unmet);
    return isNew;
  }

  function check(field) {
    var message = dateProblem(field);
    return { message: message, isNew: showProblem(field, message) };
  }

  // Capture on document runs before htmx's submit listener on the form.
  document.addEventListener(
    "submit",
    function (event) {
      var first = null;
      event.target.querySelectorAll(DATE_FIELD).forEach(function (field) {
        if (check(field).message && !first) first = field;
      });
      if (!first) return;
      event.preventDefault();
      event.stopPropagation();
      first.focus();
    },
    true,
  );

  // The field commits its text on leaving it, also when Tab only moves to its
  // own calendar button, and ownValidity is up to date by then.
  document.addEventListener("change", function (event) {
    if (event.target.localName !== DATE_FIELD) return;
    var result = check(event.target);
    if (result.isNew && liveRegion) liveRegion.announce(result.message);
  });

  document.addEventListener("focusout", function (event) {
    if (event.relatedTarget) return;
    var path = event.composedPath();
    var field = path.find(function (el) {
      return el.localName === DATE_FIELD;
    });
    var inPicker = path.some(function (el) {
      return el.localName === "nldd-date-picker";
    });
    if (!field || !inPicker) return;
    // After the field's own close handling, which runs in a microtask.
    requestAnimationFrame(function () {
      if (document.activeElement && document.activeElement !== document.body)
        return;
      var trigger =
        field.shadowRoot &&
        field.shadowRoot.querySelector(
          ".date-field__picker-button nldd-icon-button",
        );
      (trigger || field).focus();
    });
  });
})();
