/**
 * Organization tree picker for assignment forms.
 *
 * Produces the same UI (table with radios + remove buttons) from two
 * sources:
 *   - existing hidden inputs on page load / HTMX swap, so inline edit
 *     and a re-rendered create form after validation error look the
 *     same as after a fresh "apply" from the modal;
 *   - OrgTreePicker.onApply, when the user applies a new selection in
 *     the modal.
 *
 * The widget template renders just the hidden inputs (plus a
 * data-org-name carrying the label for JS rehydration). All visible
 * selection UI lives here — one code path.
 */
(function () {
  "use strict";

  var INPUTS_ID = "assignment-org-inputs";
  var SELECTIONS_ID = "assignment-org-selections";
  var TRIGGER_TEXT_ID = "assignment-org-trigger-text";

  function updateOrgTriggerText(rows) {
    var triggerText = document.getElementById(TRIGGER_TEXT_ID);
    if (!triggerText) return;
    if (!rows || rows.length === 0) {
      triggerText.textContent = "";
      var ph = document.createElement("span");
      ph.className = "org-filter-trigger__placeholder";
      ph.textContent = "Selecteer";
      triggerText.appendChild(ph);
    } else if (rows.length === 1) {
      triggerText.textContent = rows[0].label || "1 geselecteerd";
    } else {
      triggerText.textContent = rows.length + " geselecteerd";
    }
  }

  function rowsFromInputs() {
    var inputsContainer = document.getElementById(INPUTS_ID);
    if (!inputsContainer) return [];
    var rows = [];
    inputsContainer
      .querySelectorAll("input[name$='-organization']")
      .forEach(function (inp) {
        rows.push({
          nodeId: inp.value,
          label: inp.dataset.orgName || inp.value,
          role: inp.dataset.orgRole || "INVOLVED",
        });
      });
    return rows;
  }

  function rebuildInputs(rows) {
    var inputsContainer = document.getElementById(INPUTS_ID);
    if (!inputsContainer) return;
    inputsContainer.innerHTML = "";

    var mgmt = [
      ["org-TOTAL_FORMS", String(rows.length)],
      ["org-INITIAL_FORMS", "0"],
      ["org-MIN_NUM_FORMS", "1"],
      ["org-MAX_NUM_FORMS", "1000"],
    ];
    mgmt.forEach(function (pair) {
      var i = document.createElement("input");
      i.type = "hidden";
      i.name = pair[0];
      i.value = pair[1];
      inputsContainer.appendChild(i);
    });

    rows.forEach(function (row, i) {
      var orgInput = document.createElement("input");
      orgInput.type = "hidden";
      orgInput.name = "org-" + i + "-organization";
      orgInput.value = row.nodeId;
      orgInput.dataset.orgId = row.nodeId;
      orgInput.dataset.orgName = row.label;
      orgInput.dataset.orgRole = row.role;
      inputsContainer.appendChild(orgInput);

      var roleInput = document.createElement("input");
      roleInput.type = "hidden";
      roleInput.name = "org-" + i + "-role";
      roleInput.value = row.role;
      inputsContainer.appendChild(roleInput);
    });
  }

  function renderTable(rows) {
    var displayContainer = document.getElementById(SELECTIONS_ID);
    if (!displayContainer) return;
    displayContainer.innerHTML = "";

    // Guarantee exactly one PRIMARY when there's at least one row.
    if (
      rows.length > 0 &&
      !rows.some(function (r) {
        return r.role === "PRIMARY";
      })
    ) {
      rows[0].role = "PRIMARY";
    }

    if (rows.length === 0) {
      rebuildInputs(rows);
      updateOrgTriggerText(rows);
      return;
    }

    var table = document.createElement("table");
    table.className = "assignment-org-table";
    var thead = document.createElement("thead");
    var headerRow = document.createElement("tr");
    ["Organisatie", "Primaire opdrachtgever"].forEach(function (text) {
      var th = document.createElement("th");
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    var tbody = document.createElement("tbody");

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
        rebuildInputs(rows);
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
        var next = rows.filter(function (r) {
          return r.nodeId !== row.nodeId;
        });
        rows.length = 0;
        next.forEach(function (r) {
          rows.push(r);
        });
        renderTable(rows);
      });
      actionsWrapper.appendChild(removeBtn);

      tdActions.appendChild(actionsWrapper);
      tr.appendChild(tdActions);
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    displayContainer.appendChild(table);

    rebuildInputs(rows);
    updateOrgTriggerText(rows);
  }

  function renderFromInputs() {
    if (!document.getElementById(INPUTS_ID)) return;
    var rows = rowsFromInputs();
    renderTable(rows);
  }

  function initModalPicker() {
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
        // Preserve roles for orgs that were already selected.
        var existingRoles = {};
        rowsFromInputs().forEach(function (r) {
          existingRoles[r.nodeId] = r.role;
        });

        var rows = [];
        var isFirst = true;
        treeState.explicitSelections.forEach(function (label, nodeId) {
          if (
            String(nodeId).startsWith("group-") ||
            String(nodeId).startsWith("self-")
          )
            return;
          rows.push({
            nodeId: nodeId,
            label: label,
            role: existingRoles[nodeId] || (isFirst ? "PRIMARY" : "INVOLVED"),
          });
          isFirst = false;
        });
        renderTable(rows);

        var dialog = document.getElementById("assignmentOrgPickerModal");
        if (dialog) dialog.close();
      },
    });
  }

  // The trigger button's htmx:configRequest listener adds the params
  // /client-modal needs (current orgs for pre-check, count_mode=none
  // so the endpoint returns the assignment picker template). Idempotent —
  // runs on page load AND each HTMX swap, wiring the button exactly once.
  function wireTriggerButton() {
    var btn = document.getElementById("assignment-org-trigger-btn");
    if (!btn || btn.__orgTreeWired) return;
    btn.__orgTreeWired = true;
    btn.addEventListener("htmx:configRequest", function (e) {
      var orgIds = [];
      document
        .querySelectorAll("#" + INPUTS_ID + " input[data-org-id]")
        .forEach(function (inp) {
          if (inp.dataset.orgId) orgIds.push(inp.dataset.orgId);
        });
      e.detail.parameters["count_mode"] = "none";
      if (orgIds.length) {
        e.detail.parameters["org"] = orgIds;
      }
    });
  }

  document.body.addEventListener("htmx:afterSettle", function (e) {
    if (e.detail.target && e.detail.target.id === "assignmentOrgModal") {
      initModalPicker();
    }
    // The widget may have swapped in as part of an inline-edit
    // partial — re-wire the trigger and rebuild the selection UI from
    // the newly-inserted hidden inputs.
    wireTriggerButton();
    renderFromInputs();
  });

  // Page load: the create form ships the widget inline and inline edit
  // relies on the htmx:afterSettle branch above.
  wireTriggerButton();
  renderFromInputs();
})();
