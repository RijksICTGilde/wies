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

    // Ensure remove button exists
    var removeSlot = row.querySelector(".service-field--remove");
    if (removeSlot) {
      removeSlot.innerHTML = "";
      var removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className =
        "service-row__remove rvo-button rvo-button--tertiary rvo-button--size-xs";
      removeBtn.textContent = "×";
      removeBtn.title = "Dienst verwijderen";
      removeBtn.setAttribute("aria-label", "Dienst verwijderen");
      removeBtn.addEventListener("click", function () {
        row.remove();
      });
      removeSlot.appendChild(removeBtn);
    }

    // Clear any error messages
    row.querySelectorAll(".rvo-form-field__error").forEach(function (el) {
      el.remove();
    });

    container.appendChild(row);
    totalFormsInput.value = index + 1;

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
  // Inline create toggles: new skill / new colleague
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

  // --------------------------------------------------------------------------
  // Cancel button
  // --------------------------------------------------------------------------
  var cancelBtn = document.getElementById("assignment-cancel-btn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", function () {
      window.location.href = cancelBtn.dataset.cancelUrl || "/";
    });
  }

  // --------------------------------------------------------------------------
  // Remove org from data list
  // --------------------------------------------------------------------------
  function updateOrgTriggerText() {
    var inputsContainer = document.getElementById("assignment-org-inputs");
    var triggerText = document.getElementById("assignment-org-trigger-text");
    if (!inputsContainer || !triggerText) return;
    var count = inputsContainer.querySelectorAll("input").length;
    if (count === 0) {
      triggerText.textContent = "";
      var placeholder = document.createElement("span");
      placeholder.className = "org-filter-trigger__placeholder";
      placeholder.textContent = "Selecteer";
      triggerText.appendChild(placeholder);
    } else if (count === 1) {
      var dl = document.querySelector("#assignment-org-selections dt");
      triggerText.textContent = dl ? dl.textContent : "1 geselecteerd";
    } else {
      triggerText.textContent = count + " geselecteerd";
    }
  }

  // --------------------------------------------------------------------------
  // Pass current org selections to modal so they are pre-checked on reopen
  // --------------------------------------------------------------------------
  document.body.addEventListener("htmx:configRequest", function (e) {
    var elt = e.detail.elt;
    if (!elt || !elt.closest("#assignment-org-picker")) return;
    var inputs = document.querySelectorAll("#assignment-org-inputs input");
    inputs.forEach(function (inp) {
      if (inp.value) {
        e.detail.path += "&org=" + encodeURIComponent(inp.value);
      }
    });
  });

  document.body.addEventListener("click", function (e) {
    var removeBtn = e.target.closest(".assignment-org-remove");
    if (!removeBtn) return;

    var orgId = removeBtn.dataset.orgId;

    var inputsContainer = document.getElementById("assignment-org-inputs");
    if (inputsContainer) {
      var input = inputsContainer.querySelector('input[value="' + orgId + '"]');
      if (input) input.remove();
    }

    var wasPrimary = false;
    var tr = removeBtn.closest("tr");
    if (tr) {
      var radio = tr.querySelector("input[type='radio']");
      wasPrimary = radio && radio.checked;
      tr.remove();
    }

    // If we removed the primary, promote the first remaining org
    if (wasPrimary && inputsContainer) {
      var firstInput = inputsContainer.querySelector("input[data-org-id]");
      if (firstInput) {
        firstInput.name = "primary_organization";
        var displayContainer = document.getElementById(
          "assignment-org-selections",
        );
        if (displayContainer) {
          var firstRadio = displayContainer.querySelector(
            "input[type='radio']",
          );
          if (firstRadio) firstRadio.checked = true;
        }
      }
    }

    var displayContainer = document.getElementById("assignment-org-selections");
    var table = displayContainer
      ? displayContainer.querySelector(".assignment-org-table")
      : null;
    if (table) {
      var tbody = table.querySelector("tbody");
      if (tbody && tbody.children.length === 0) table.remove();
    }

    updateOrgTriggerText();
  });
})();
