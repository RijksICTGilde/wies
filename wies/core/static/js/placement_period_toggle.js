// Wires the period block (see period_fields.js) for the placement edit panel
// and the generic inline-edit form. The date fields stay enabled so they post
// along; with period_source=SERVICE the server uses the assignment period.
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

    window.WiesPeriodFields({
      group,
      checkbox,
      startInput,
      endInput,
      endKnownSwitch,
      periodHelp: servicePeriodHelp,
      inheritStart: serviceStart ?? "",
      inheritEnd: serviceEnd ?? "",
      writeInherit: (inherit) => {
        if (hiddenSelect)
          hiddenSelect.value = inherit ? "SERVICE" : "PLACEMENT";
      },
    });
  }

  function scan(root) {
    (root || document)
      .querySelectorAll("[data-period-choice], #placement-inherit-period")
      // The team-member form has its own handler in member_form.js.
      .forEach((el) => {
        if (!el.closest("[data-member-form]")) init(el);
      });
  }

  document.addEventListener("DOMContentLoaded", () => scan(document));
  document.addEventListener("htmx:afterSwap", (e) => scan(e.detail.target));
})();
