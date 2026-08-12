// Ties the period choice to the date fields, in two supported shapes:
//   - nldd-segmented-control[data-period-choice]  (placement edit panel)
//   - nldd-checkbox-field #placement-inherit-period (generic inline-edit form)
//
// Inheriting from the assignment hides the date fields and fills them with the
// assignment period; the hidden period_source select carries the posted value.
// The fields stay enabled so they post along — with period_source=SERVICE the
// server uses the assignment period anyway.
//
// The [data-end-date-known] switch only drives the end date field (off means
// "runs on", so an empty end date) and does not post itself.
(function () {
  function init(control) {
    if (!control || control.dataset.periodToggleInit) return;
    control.dataset.periodToggleInit = "true";
    const group = control.hasAttribute("data-period-choice") ? control : null;
    const checkbox = group ? null : control;

    const form = control.closest("form");
    if (!form) return;

    // By name, not by data attribute: the widget templates do not pass
    // arbitrary data-* through to the NLDD fields, so those hooks never reach
    // the DOM.
    const hiddenSelect = form.querySelector("[name=period_source]");
    // The assignment period sits on the panel form or, for the generic
    // inline-edit, on the [data-placement-period] body wrapper: there the form
    // element belongs to the wrapper and carries no service data.
    const periodRoot = form.querySelector("[data-placement-period]") || form;
    const serviceStart = periodRoot.dataset.serviceStart || null;
    const serviceEnd = periodRoot.dataset.serviceEnd || null;
    const startInput = form.querySelector("[name=specific_start_date]");
    const endInput = form.querySelector("[name=specific_end_date]");
    const endKnownSwitch = form.querySelector("[data-end-date-known]");
    const servicePeriodHelp = form.querySelector("[data-service-period-help]");

    // Hide the whole field, not just the input, or the label stays behind.
    // Without an nldd-form-field (the older inline-edit form) it falls back to
    // the input itself.
    const fieldOf = (el) => el && (el.closest("nldd-form-field") || el);
    const startField = fieldOf(startInput);
    const endField = fieldOf(endInput);
    const endKnownField = fieldOf(endKnownSwitch);

    function inheritsFromService() {
      if (!group) return checkbox.checked;
      return group.getAttribute("value") !== "PLACEMENT";
    }

    function endDateKnown() {
      return !endKnownSwitch || endKnownSwitch.hasAttribute("checked");
    }

    // Remembers the last end date the user entered, so toggling the switch off
    // and on again does not wipe it. The assignment period written into the
    // field is not the user's choice and is deliberately not remembered.
    let lastEndDate = endInput ? endInput.value : "";

    /**
     * Applies a period choice to the visible fields and the posted values.
     *
     * @param {boolean} inherit True to take the period from the assignment;
     *     false to use the placement's own dates.
     * @param {boolean|undefined} knownOverride The end-date-known state to use
     *     instead of reading the switch, or undefined to read it.
     */
    function update(inherit, knownOverride) {
      if (hiddenSelect) hiddenSelect.value = inherit ? "SERVICE" : "PLACEMENT";
      if (servicePeriodHelp) servicePeriodHelp.hidden = !inherit;
      if (startField) startField.hidden = inherit;
      if (endKnownField) endKnownField.hidden = inherit;
      // The end date also disappears when the user says there is none.
      // knownOverride comes from the change event, where the switch's attribute
      // is not updated yet.
      const known =
        knownOverride === undefined ? endDateKnown() : knownOverride;
      if (endField) endField.hidden = inherit || !known;
      if (inherit) {
        if (startInput) startInput.value = serviceStart ?? "";
        if (endInput) endInput.value = serviceEnd ?? "";
      } else if (endInput) {
        // Empty means "runs on"; keep the entered date for when the switch
        // comes back on.
        if (!known) {
          if (endInput.value) lastEndDate = endInput.value;
          endInput.value = "";
        } else if (!endInput.value) {
          endInput.value = lastEndDate;
        }
      }
    }

    if (group) {
      // nldd-segmented-control bubbles a change carrying detail.value.
      group.addEventListener("change", (e) => {
        const value = e.detail && e.detail.value;
        update(value ? value === "SERVICE" : inheritsFromService());
      });
    } else {
      // nldd-checkbox-field bubbles a change carrying detail.checked; the
      // property is already updated by then, so both read the same.
      checkbox.addEventListener("change", (e) =>
        update(e.detail ? e.detail.checked : checkbox.checked),
      );
    }

    if (endKnownSwitch) {
      endKnownSwitch.addEventListener("change", (e) => {
        const known = e.detail ? e.detail.checked : endDateKnown();
        update(inheritsFromService(), known);
      });
    }

    update(inheritsFromService());
  }

  function scan(root) {
    (root || document)
      .querySelectorAll("[data-period-choice], #placement-inherit-period")
      .forEach(init);
  }

  document.addEventListener("DOMContentLoaded", () => scan(document));
  document.addEventListener("htmx:afterSwap", (e) => scan(e.detail.target));
})();
