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
    var count = inputsContainer.querySelectorAll(
      "input[name$='-organization']",
    ).length;
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
        inputsContainer
          .querySelectorAll("[data-org-id]")
          .forEach(function (inp) {
            existingRoles[inp.dataset.orgId] =
              inp.dataset.orgRole || "INVOLVED";
          });

        inputsContainer.innerHTML = "";
        displayContainer.innerHTML = "";

        var hasSelections = false;
        var isFirst = true;
        var index = 0;
        var rows = [];

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

          rows.push({
            nodeId: nodeId,
            label: label,
            role: defaultRole,
            index: index,
          });
          index++;
          isFirst = false;
        });

        function rebuildInputs() {
          inputsContainer.innerHTML = "";

          // Formset management form
          var totalForms = document.createElement("input");
          totalForms.type = "hidden";
          totalForms.name = "org-TOTAL_FORMS";
          totalForms.value = rows.length;
          inputsContainer.appendChild(totalForms);

          var initialForms = document.createElement("input");
          initialForms.type = "hidden";
          initialForms.name = "org-INITIAL_FORMS";
          initialForms.value = "0";
          inputsContainer.appendChild(initialForms);

          var minForms = document.createElement("input");
          minForms.type = "hidden";
          minForms.name = "org-MIN_NUM_FORMS";
          minForms.value = "1";
          inputsContainer.appendChild(minForms);

          var maxForms = document.createElement("input");
          maxForms.type = "hidden";
          maxForms.name = "org-MAX_NUM_FORMS";
          maxForms.value = "1000";
          inputsContainer.appendChild(maxForms);

          rows.forEach(function (row, i) {
            var orgInput = document.createElement("input");
            orgInput.type = "hidden";
            orgInput.name = "org-" + i + "-organization";
            orgInput.value = row.nodeId;
            orgInput.dataset.orgId = row.nodeId;
            orgInput.dataset.orgRole = row.role;
            inputsContainer.appendChild(orgInput);

            var roleInput = document.createElement("input");
            roleInput.type = "hidden";
            roleInput.name = "org-" + i + "-role";
            roleInput.value = row.role;
            inputsContainer.appendChild(roleInput);
          });
        }

        rows.forEach(function (row) {
          var tr = document.createElement("tr");

          var tdName = document.createElement("td");
          tdName.textContent = row.label;
          tr.appendChild(tdName);

          var tdActions = document.createElement("td");
          var actionsWrapper = document.createElement("div");
          actionsWrapper.className = "assignment-org-table__actions";

          var radioLabel = document.createElement("label");
          radioLabel.className = "rvo-radio-button";
          var radio = document.createElement("input");
          radio.type = "radio";
          radio.name = "primary_org_radio";
          radio.value = row.nodeId;
          radio.className = "utrecht-radio-button";
          if (row.role === "PRIMARY") radio.checked = true;
          radio.addEventListener("change", function () {
            rows.forEach(function (r) {
              r.role = r.nodeId === radio.value ? "PRIMARY" : "INVOLVED";
            });
            rebuildInputs();
          });
          radioLabel.appendChild(radio);
          actionsWrapper.appendChild(radioLabel);

          var removeBtn = document.createElement("button");
          removeBtn.type = "button";
          removeBtn.className =
            "assignment-org-remove rvo-button rvo-button--tertiary rvo-button--size-xs";
          removeBtn.dataset.orgId = row.nodeId;
          removeBtn.textContent = "Verwijderen";
          removeBtn.setAttribute("aria-label", "Verwijder " + row.label);
          removeBtn.addEventListener("click", function () {
            rows = rows.filter(function (r) {
              return r.nodeId !== row.nodeId;
            });
            if (
              rows.length > 0 &&
              !rows.some(function (r) {
                return r.role === "PRIMARY";
              })
            ) {
              rows[0].role = "PRIMARY";
            }
            rebuildInputs();
            tr.remove();
            if (rows.length === 0) table.remove();
            updateOrgTriggerText();
          });
          actionsWrapper.appendChild(removeBtn);

          tdActions.appendChild(actionsWrapper);
          tr.appendChild(tdActions);
          tbody.appendChild(tr);
        });

        // Ensure exactly one primary
        if (
          hasSelections &&
          !rows.some(function (r) {
            return r.role === "PRIMARY";
          })
        ) {
          rows[0].role = "PRIMARY";
          var firstRadio = tbody.querySelector("input[type='radio']");
          if (firstRadio) firstRadio.checked = true;
        }

        rebuildInputs();

        table.appendChild(tbody);
        if (hasSelections) {
          displayContainer.appendChild(table);
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

  var triggerBtn = document.getElementById("assignment-org-trigger-btn");
  if (triggerBtn) {
    triggerBtn.addEventListener("htmx:configRequest", function (e) {
      var params = new URLSearchParams(e.detail.path.split("?")[1] || "");
      // Include orgs from JS-managed inputs (data-org-id) and server-rendered inputs
      document
        .querySelectorAll("#assignment-org-inputs input[data-org-id]")
        .forEach(function (inp) {
          params.append("org", inp.dataset.orgId);
        });
      document
        .querySelectorAll("#assignment-org-inputs input[name$='-organization']")
        .forEach(function (inp) {
          if (inp.value) params.append("org", inp.value);
        });
      e.detail.path = e.detail.path.split("?")[0] + "?" + params.toString();
    });
  }

  // On page load, update trigger text in case org data was preserved after form error
  updateOrgTriggerText();
})();
