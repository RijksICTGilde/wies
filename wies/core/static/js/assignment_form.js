/**
 * Services formset behaviours: dynamic row add/remove, status-reveals-details,
 * inline skill creation, and create-form-specific cancel + error-scroll helpers.
 *
 * Runs on DOMContentLoaded AND on htmx:afterSwap so the side-panel
 * inline-edit form (which injects the same services-container into
 * the DOM) gets the same behaviour — this matches the existing pattern
 * in multi_select.js / dialog.js / filters.js.
 */
(function () {
  function initServicesForm() {
    var container = document.querySelector("#services-container");
    if (!container) return;
    if (container.dataset.servicesFormInitialized === "1") return;
    var totalFormsInput = document.querySelector("#id_service-TOTAL_FORMS");
    if (!totalFormsInput) return;
    container.dataset.servicesFormInitialized = "1";

    // Hide the single empty template row on page load.
    var initialRows = container.querySelectorAll(".service-row");
    if (
      initialRows.length === 1 &&
      initialRows[0].dataset.hasChoice === "false"
    ) {
      initialRows[0].style.display = "none";
      initialRows[0].dataset.hiddenTemplate = "1";
    }

    function updateRemoveButtons() {
      var visibleRows = container.querySelectorAll(
        ".service-row:not([data-hidden-template='1'])",
      );
      visibleRows.forEach(function (row) {
        var actionsDiv = row.querySelector(".service-row__actions");
        if (!actionsDiv) return;
        var existing = actionsDiv.querySelector(".service-row__remove");
        if (visibleRows.length > 1) {
          if (!existing) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className =
              "service-row__remove rvo-button rvo-button--warning-subtle rvo-button--size-sm";
            btn.textContent = "Verwijderen";
            btn.setAttribute("aria-label", "Dienst verwijderen");
            btn.addEventListener("click", function () {
              row.remove();
              updateRemoveButtons();
            });
            actionsDiv.appendChild(btn);
          }
        } else {
          if (existing) existing.remove();
        }
      });
    }

    function addServiceRow(status) {
      var index = parseInt(totalFormsInput.value, 10);

      // Use the hidden template row for the first add, clone for subsequent.
      var templateRow = container.querySelector("[data-hidden-template='1']");
      var row;
      if (templateRow) {
        row = templateRow;
        row.style.display = "";
        delete row.dataset.hiddenTemplate;
      } else {
        var sourceRow = container.querySelector(".service-row");
        row = sourceRow.cloneNode(true);
        row.dataset.serviceIndex = index;

        row
          .querySelectorAll("input, select, textarea")
          .forEach(function (field) {
            if (field.name)
              field.name = field.name.replace(/-\d+-/, "-" + index + "-");
            if (field.id)
              field.id = field.id.replace(/-\d+-/, "-" + index + "-");
            if (field.tagName === "SELECT") {
              field.selectedIndex = 0;
            } else if (field.type === "radio") {
              field.checked = false;
            } else if (field.type === "checkbox") {
              field.checked = false;
            } else {
              field.value = "";
            }
          });
        row.querySelectorAll("label").forEach(function (label) {
          var forAttr = label.getAttribute("for");
          if (forAttr)
            label.setAttribute(
              "for",
              forAttr.replace(/-\d+-/, "-" + index + "-"),
            );
        });

        var newSkill = row.querySelector(".service-new-skill");
        if (newSkill) newSkill.style.display = "none";

        var existingBtn = row.querySelector(".service-row__remove");
        if (existingBtn) existingBtn.remove();

        row.querySelectorAll(".rvo-form-field__error").forEach(function (el) {
          el.remove();
        });

        container.appendChild(row);
        totalFormsInput.value = index + 1;
      }

      // Pre-select the chosen status radio.
      var radio = row.querySelector(
        "input[type='radio'][value='" + status + "']",
      );
      if (radio) {
        radio.checked = true;
        row.dataset.hasChoice = "true";
      }

      // Show details immediately (status already chosen).
      var details = row.querySelector(".service-row__details");
      if (details) details.style.display = "";

      // For "aanvraag", hide consultant field as it's not relevant.
      if (status === "aanvraag") {
        var colleagueField = row.querySelector(".service-colleague-field");
        if (colleagueField) colleagueField.style.display = "none";
      } else {
        var colleagueField = row.querySelector(".service-colleague-field");
        if (colleagueField) colleagueField.style.display = "";
      }

      updateRemoveButtons();
      initInlineCreate(row);
      initColleagueToggle(row);
      initPeriodToggles();
    }

    function initColleagueToggle(row) {
      var radios = row.querySelectorAll(
        ".service-row__status-toggle input[type='radio']",
      );
      var colleagueField = row.querySelector(".service-colleague-field");
      if (!colleagueField) return;
      radios.forEach(function (radio) {
        radio.addEventListener("change", function () {
          colleagueField.style.display =
            radio.value === "aanvraag" ? "none" : "";
        });
      });
    }

    // Bind the two add buttons.
    document.querySelectorAll("[data-add-service]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        addServiceRow(btn.dataset.addService);
      });
    });

    function initInlineCreate(row) {
      var skillSelect = row.querySelector("[name$='-skill']");
      var newSkillDiv = row.querySelector(".service-new-skill");
      if (skillSelect && newSkillDiv) {
        skillSelect.addEventListener("change", function () {
          newSkillDiv.style.display =
            skillSelect.value === "__new__" ? "" : "none";
        });
      }
    }

    container.querySelectorAll(".service-row").forEach(function (row) {
      initInlineCreate(row);
      initPeriodToggles();
      initColleagueToggle(row);
    });
    updateRemoveButtons();
  }

  function initPeriodToggles() {
    // Assignment dates: from the create form inputs, or from data attributes
    // on the services container (set by the inline-edit template).
    var assignmentStartEl = document.querySelector("#id_start_date");
    var assignmentEndEl = document.querySelector("#id_end_date");
    var container = document.querySelector("#services-container");
    var assignmentStartAttr = container && container.dataset.assignmentStart;
    var assignmentEndAttr = container && container.dataset.assignmentEnd;

    document.querySelectorAll(".service-row").forEach(function (row) {
      if (row.dataset.periodToggleInit === "1") return;
      var checkbox = row.querySelector("[name$='-has_custom_period']");
      if (!checkbox) return;
      var startInput = row.querySelector("[name$='-placement_start_date']");
      var endInput = row.querySelector("[name$='-placement_end_date']");
      if (!startInput || !endInput) return;
      row.dataset.periodToggleInit = "1";

      // Hint element shown when checkbox is checked but assignment has no dates.
      var hint = row.querySelector(".service-period-hint");
      if (!hint) {
        hint = document.createElement("p");
        hint.className = "service-period-hint rvo-text--sm rvo-text--subtle";
        hint.style.display = "none";
        hint.textContent = "Vul eerst de opdrachtperiode in hierboven.";
        checkbox.closest(".service-period-section").appendChild(hint);
      }

      function getAssignmentStart() {
        return (assignmentStartEl && assignmentStartEl.value) || assignmentStartAttr || "";
      }
      function getAssignmentEnd() {
        return (assignmentEndEl && assignmentEndEl.value) || assignmentEndAttr || "";
      }

      function updateDateFields() {
        startInput.disabled = checkbox.checked;
        endInput.disabled = checkbox.checked;
        if (checkbox.checked) {
          var aStart = getAssignmentStart();
          var aEnd = getAssignmentEnd();
          if (aStart) startInput.value = aStart;
          if (aEnd) endInput.value = aEnd;
          hint.style.display = (!aStart && !aEnd) ? "" : "none";
        } else {
          hint.style.display = "none";
        }
      }

      checkbox.addEventListener("change", updateDateFields);
      updateDateFields();

      // Also update when assignment dates change.
      if (assignmentStartEl) assignmentStartEl.addEventListener("change", function () {
        if (checkbox.checked) startInput.value = assignmentStartEl.value;
      });
      if (assignmentEndEl) assignmentEndEl.addEventListener("change", function () {
        if (checkbox.checked) endInput.value = assignmentEndEl.value;
      });
    });
  }

  function initCancelButton() {
    var cancelBtn = document.getElementById("assignment-cancel-btn");
    if (!cancelBtn || cancelBtn.dataset.cancelInitialized === "1") return;
    cancelBtn.dataset.cancelInitialized = "1";
    cancelBtn.addEventListener("click", function () {
      window.location.href = cancelBtn.dataset.cancelUrl || "/";
    });
  }

  function scrollToDienstenError() {
    var err = document.getElementById("diensten-error");
    if (err) err.scrollIntoView({ behavior: "smooth" });
  }

  function initAll() {
    initServicesForm();
    initPeriodToggles();
    initCancelButton();
    scrollToDienstenError();
  }

  document.addEventListener("DOMContentLoaded", initAll);
  document.addEventListener("htmx:afterSwap", initAll);
})();
