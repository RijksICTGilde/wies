/**
 * Assignment creation form: dynamic service formset rows, status toggle,
 * inline create toggles, and org picker chip management.
 */
(function () {
  var container = document.getElementById("services-container");
  var addBtn = document.getElementById("add-service-btn");
  var totalFormsInput = document.getElementById("id_service-TOTAL_FORMS");

  if (!container || !addBtn || !totalFormsInput) return;

  // --------------------------------------------------------------------------
  // Remove buttons: show on all rows when >1, hide when only 1 remains
  // --------------------------------------------------------------------------
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

  // --------------------------------------------------------------------------
  // Dynamic formset rows
  // --------------------------------------------------------------------------
  function addServiceRow() {
    var index = parseInt(totalFormsInput.value, 10);
    var firstRow = container.querySelector(".service-row");
    var row = firstRow.cloneNode(true);
    row.dataset.serviceIndex = index;

    // Update all input/select name, id, for attributes from index 0 to new index
    row.querySelectorAll("input, select, textarea").forEach(function (field) {
      if (field.name) field.name = field.name.replace(/-0-/, "-" + index + "-");
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

    // Hide inline create fields and colleague row
    row
      .querySelectorAll(".service-new-skill, .service-colleague-field")
      .forEach(function (el) {
        el.style.display = "none";
      });

    // Remove any existing remove button from the clone (updateRemoveButtons handles it)
    var existingBtn = row.querySelector(".service-row__remove");
    if (existingBtn) existingBtn.remove();

    // Clear any error messages
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

  // --------------------------------------------------------------------------
  // Per-service toggle: show/hide consultant field when "Collega gevonden"
  // --------------------------------------------------------------------------
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

  // --------------------------------------------------------------------------
  // Inline create toggles: new skill
  // --------------------------------------------------------------------------
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

  // Init for existing rows
  container.querySelectorAll(".service-row").forEach(function (row) {
    initStatusToggle(row);
    initInlineCreate(row);
  });
  updateRemoveButtons();

  // --------------------------------------------------------------------------
  // Cancel button
  // --------------------------------------------------------------------------
  var cancelBtn = document.getElementById("assignment-cancel-btn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", function () {
      window.location.href = cancelBtn.dataset.cancelUrl || "/";
    });
  }

  var dienstenError = document.getElementById("diensten-error");
  if (dienstenError) {
    dienstenError.scrollIntoView({ behavior: "smooth" });
  }
})();
