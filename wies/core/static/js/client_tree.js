/**
 * Client tree picker for placement filters.
 * Thin wrapper around OrgTreePicker with filter-specific apply/clear logic.
 */
(function () {
  "use strict";

  function updateResultsCount(treeState) {
    var resultsEl = document.getElementById("client-results-count");
    if (!resultsEl) return;
    var total = 0;
    treeState.explicitSelections.forEach(function (label, nodeId) {
      var node = treeState.getNode(nodeId);
      if (node && node.nr_of_placements !== undefined) {
        total += node.nr_of_placements;
      }
    });
    resultsEl.textContent = total > 0 ? total + " plaatsingen" : "";
  }

  function init() {
    new OrgTreePicker({
      dataElementId: "client-data",
      containerId: "client-tree-container",
      selectionListId: "client-selection-list",
      searchInputId: "client-search",
      clearBtnId: "client-clear-btn",
      applyBtnId: "client-apply-btn",
      countElementId: "client-selection-count",
      currentSelectionsId: "client-current-selections",
      checkboxIdPrefix: "client-node-",
      showBadges: true,
      expandOnCheck: true,
      onSync: updateResultsCount,
      onApply: function (treeState) {
        var orgInputsContainer = document.getElementById("org-filter-inputs");
        var sidebarForm = document.querySelector(".filter-sidebar-form");
        if (orgInputsContainer) {
          orgInputsContainer.innerHTML = "";
          for (var entry of treeState.explicitSelections) {
            var nodeId = entry[0];
            var label = entry[1];
            var input = document.createElement("input");
            input.type = "hidden";
            input.dataset.filterInput = "";
            input.dataset.label = label;
            if (nodeId.startsWith("self-")) {
              input.name = "org_self";
              input.value = nodeId.slice(5);
            } else if (nodeId.startsWith("group-")) {
              input.name = "org_type";
              input.value = nodeId.slice(6);
            } else {
              input.name = "org";
              input.value = nodeId;
            }
            orgInputsContainer.appendChild(input);
          }
        }

        var dialog = document.getElementById("clientModal");
        if (dialog) dialog.close();

        updateOrgFilterButtonText();
        if (sidebarForm) {
          htmx.trigger(sidebarForm, "change");
        }
      },
      onClear: function () {
        var orgInputsContainer = document.getElementById("org-filter-inputs");
        var sidebarForm = document.querySelector(".filter-sidebar-form");
        if (orgInputsContainer) orgInputsContainer.innerHTML = "";

        var dialog = document.getElementById("clientModal");
        if (dialog) dialog.close();

        updateOrgFilterButtonText();
        if (sidebarForm) htmx.trigger(sidebarForm, "change");
      },
    });
  }

  document.body.addEventListener("htmx:afterSettle", function (e) {
    if (e.detail.target && e.detail.target.id === "clientModalContainer") {
      init();
    }
  });
})();
