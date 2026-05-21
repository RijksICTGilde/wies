/**
 * Services formset behaviours: dynamic row add/remove, "Rol ingevuld"
 * colleague reveal, inline skill creation, and create-form-specific
 * cancel + error-scroll helpers.
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
    // HTMX swaps replace the node wholesale, so this flag is fresh on
    // each swap. The guard protects against repeat DOMContentLoaded /
    // afterSwap firings against the same node.
    if (container.dataset.servicesFormInitialized === "1") return;
    var addBtn = document.querySelector("#add-service-btn");
    var totalFormsInput = document.querySelector("#id_service-TOTAL_FORMS");
    if (!addBtn || !totalFormsInput) return;
    container.dataset.servicesFormInitialized = "1";

    function updateRemoveButtons() {
      var rows = container.querySelectorAll(".service-row");
      rows.forEach(function (row) {
        var checkboxLine = row.querySelector(".service-row__checkbox-line");
        if (!checkboxLine) return;
        var existing = checkboxLine.querySelector(".service-row__remove");
        if (rows.length > 1) {
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
            checkboxLine.appendChild(btn);
          }
        } else {
          if (existing) existing.remove();
        }
      });
    }

    function addServiceRow() {
      var index = parseInt(totalFormsInput.value, 10);
      var firstRow = container.querySelector(".service-row");
      var row = firstRow.cloneNode(true);
      row.dataset.serviceIndex = index;

      row.querySelectorAll("input, select, textarea").forEach(function (field) {
        if (field.name)
          field.name = field.name.replace(/-0-/, "-" + index + "-");
        if (field.id) field.id = field.id.replace(/-0-/, "-" + index + "-");
        if (field.tagName === "SELECT") {
          field.selectedIndex = 0;
        } else {
          field.value = "";
        }
      });
      row.querySelectorAll("label").forEach(function (label) {
        var forAttr = label.getAttribute("for");
        if (forAttr)
          label.setAttribute("for", forAttr.replace(/-0-/, "-" + index + "-"));
      });

      row
        .querySelectorAll(".service-new-skill, .service-colleague-field")
        .forEach(function (el) {
          el.style.display = "none";
        });

      var existingBtn = row.querySelector(".service-row__remove");
      if (existingBtn) existingBtn.remove();

      row.querySelectorAll(".rvo-form-field__error").forEach(function (el) {
        el.remove();
      });

      container.appendChild(row);
      totalFormsInput.value = index + 1;

      updateRemoveButtons();
      initStatusToggle(row);
      initInlineCreate(row);
    }

    addBtn.addEventListener("click", addServiceRow);

    function initStatusToggle(row) {
      var checkbox = row.querySelector("[name$='-is_filled']");
      var colleagueField = row.querySelector(".service-colleague-field");
      if (!checkbox || !colleagueField) return;

      function update() {
        colleagueField.style.display = checkbox.checked ? "" : "none";
      }

      checkbox.addEventListener("change", update);
      update();
    }

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
      initStatusToggle(row);
      initInlineCreate(row);
    });
    updateRemoveButtons();
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
    initCancelButton();
    scrollToDienstenError();
  }

  document.addEventListener("DOMContentLoaded", initAll);
  document.addEventListener("htmx:afterSwap", initAll);
})();
