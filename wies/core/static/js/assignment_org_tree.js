/**
 * Organization tree picker for assignment creation form.
 * Thin wrapper around OrgTreePicker with assignment-specific apply logic
 * (primary/involved org roles, radio buttons, table display).
 */
(function () {
  "use strict";

  function updateOrgTriggerText() {
    var inputsContainer = document.getElementById("assignment-org-inputs");
    var triggerText = document.getElementById("assignment-org-trigger-text");
    if (!inputsContainer || !triggerText) return;
    var count = inputsContainer.querySelectorAll("input").length;
    if (count === 0) {
      triggerText.textContent = "";
      var ph = document.createElement("span");
      ph.className = "org-filter-trigger__placeholder";
      ph.textContent = "Selecteer";
      triggerText.appendChild(ph);
    } else if (count === 1) {
      var dl = document.querySelector("#assignment-org-selections dt");
      triggerText.textContent = dl ? dl.textContent : "1 geselecteerd";
    } else {
      triggerText.textContent = count + " geselecteerd";
    }
  }

  function init() {
    new OrgTreePicker({
      dataElementId: "assignment-org-data",
      containerId: "assignment-org-tree-container",
      selectionListId: "assignment-org-selection-list",
      searchInputId: "assignment-org-search",
      clearBtnId: "assignment-org-clear-btn",
      applyBtnId: "assignment-org-apply-btn",
      countElementId: "assignment-org-selection-count",
      currentSelectionsId: "assignment-org-current-selections",
      checkboxIdPrefix: "asgn-org-node-",
      skipGroupCheckboxes: true,
      onApply: function (treeState) {
        var inputsContainer = document.getElementById("assignment-org-inputs");
        var displayContainer = document.getElementById(
          "assignment-org-selections",
        );
        if (!inputsContainer || !displayContainer) return;

        // Preserve existing roles before clearing
        var existingRoles = {};
        inputsContainer.querySelectorAll("input").forEach(function (inp) {
          existingRoles[inp.value] =
            inp.name === "primary_organization" ? "PRIMARY" : "INVOLVED";
        });

        inputsContainer.innerHTML = "";
        displayContainer.innerHTML = "";

        var hasSelections = false;
        var isFirst = true;
        var table = document.createElement("table");
        table.className = "assignment-org-table";
        var thead = document.createElement("thead");
        var headerRow = document.createElement("tr");
        var thOrg = document.createElement("th");
        thOrg.textContent = "Organisatie";
        headerRow.appendChild(thOrg);
        var thPrimary = document.createElement("th");
        thPrimary.textContent = "Primaire opdrachtgever";
        headerRow.appendChild(thPrimary);
        thead.appendChild(headerRow);
        table.appendChild(thead);
        var tbody = document.createElement("tbody");

        treeState.explicitSelections.forEach(function (label, nodeId) {
          if (
            String(nodeId).startsWith("group-") ||
            String(nodeId).startsWith("self-")
          )
            return;

          hasSelections = true;
          var defaultRole =
            existingRoles[nodeId] || (isFirst ? "PRIMARY" : "INVOLVED");

          var input = document.createElement("input");
          input.type = "hidden";
          input.name =
            defaultRole === "PRIMARY"
              ? "primary_organization"
              : "involved_organization";
          input.value = nodeId;
          input.dataset.orgId = nodeId;
          inputsContainer.appendChild(input);

          var tr = document.createElement("tr");

          var tdName = document.createElement("td");
          tdName.textContent = label;
          tr.appendChild(tdName);

          var tdActions = document.createElement("td");
          var actionsWrapper = document.createElement("div");
          actionsWrapper.className = "assignment-org-table__actions";

          var radioLabel = document.createElement("label");
          radioLabel.className = "rvo-radio-button";
          var radio = document.createElement("input");
          radio.type = "radio";
          radio.name = "primary_org_radio";
          radio.value = nodeId;
          radio.className = "utrecht-radio-button";
          if (defaultRole === "PRIMARY") radio.checked = true;
          radio.addEventListener("change", function () {
            inputsContainer
              .querySelectorAll("input[data-org-id]")
              .forEach(function (inp) {
                inp.name =
                  inp.dataset.orgId === radio.value
                    ? "primary_organization"
                    : "involved_organization";
              });
          });
          radioLabel.appendChild(radio);
          actionsWrapper.appendChild(radioLabel);

          var removeBtn = document.createElement("button");
          removeBtn.type = "button";
          removeBtn.className =
            "assignment-org-remove rvo-button rvo-button--tertiary rvo-button--size-xs";
          removeBtn.dataset.orgId = nodeId;
          removeBtn.textContent = "Verwijderen";
          removeBtn.setAttribute("aria-label", "Verwijder " + label);
          actionsWrapper.appendChild(removeBtn);

          tdActions.appendChild(actionsWrapper);
          tr.appendChild(tdActions);

          tbody.appendChild(tr);
          isFirst = false;
        });

        table.appendChild(tbody);
        if (hasSelections) {
          displayContainer.appendChild(table);
        }

        // Ensure exactly one primary is always selected
        var primaryRadio = tbody.querySelector("input[type='radio']:checked");
        if (!primaryRadio && hasSelections) {
          var firstRadio = tbody.querySelector("input[type='radio']");
          if (firstRadio) {
            firstRadio.checked = true;
            firstRadio.dispatchEvent(new Event("change"));
          }
        }

        updateOrgTriggerText();

        var dialog = document.getElementById("assignmentOrgPickerModal");
        if (dialog) dialog.close();
      },
    });
  }

  document.body.addEventListener("htmx:afterSettle", function (e) {
    if (e.detail.target && e.detail.target.id === "assignmentOrgModal") {
      init();
    }
  });
})();
