(function () {
  "use strict";

  var dataEl = document.getElementById("assignment-org-data");
  var data = dataEl ? JSON.parse(dataEl.textContent) : [];
  var container = document.getElementById("assignment-org-tree-container");
  var searchInput = document.getElementById("assignment-org-search");
  var applyBtn = document.getElementById("assignment-org-apply-btn");

  if (!container) return;

  // An assignment is linked to concrete organisations: type groups are
  // structure only, and picking a parent means that org, not its subtree.
  var treeState = new TreeState(data, { collapseToParent: false });
  var tree = new WiesOrgTree({
    state: treeState,
    container: container,
    showCounts: false,
    accessibleLabel: "Opdrachtgevers",
    isSelectable: function (node) {
      return !node.group;
    },
    onToggle: rebuildSelectionList,
  });
  tree.render().bindSearch(searchInput);

  // Above this many, the tokens push the CTA off-screen; the button's count
  // says the same thing.
  var MAX_VISIBLE_TOKENS = 6;

  // Group and self nodes carry no organisation, so they never reach the form.
  function selectedOrgs() {
    var rows = [];
    treeState.explicitSelections.forEach(function (label, nodeId) {
      if (nodeId.indexOf("group-") === 0 || nodeId.indexOf("self-") === 0) {
        return;
      }
      rows.push({ nodeId: nodeId, label: label });
    });
    return rows;
  }

  function updateApplyLabel(rows) {
    if (!applyBtn) return;
    applyBtn.setAttribute(
      "text",
      rows.length > 1
        ? "Voeg " + rows.length + " opdrachtgevers toe"
        : "Voeg toe",
    );
  }

  function rebuildSelectionList() {
    var rows = selectedOrgs();
    updateApplyLabel(rows);
    var box = document.getElementById("assignment-org-selection-tokens");
    if (!box) return;
    box.innerHTML = "";
    box.hidden = rows.length === 0 || rows.length > MAX_VISIBLE_TOKENS;
    if (box.hidden) return;
    rows.forEach(function (row) {
      var token = document.createElement("nldd-token");
      token.setAttribute("control", "dismiss");
      token.setAttribute("dismiss-text", "Verwijder " + row.label);
      token.textContent = row.label;
      token.addEventListener("dismiss", function () {
        treeState.removeSelection(row.nodeId);
        tree.sync();
        rebuildSelectionList();
      });
      box.appendChild(token);
    });
  }

  // assignment_org_picker.js owns the formset inputs and listens for this
  // event, so the sheet can be thrown away without the form losing state.
  if (applyBtn) {
    applyBtn.addEventListener("click", function () {
      document.dispatchEvent(
        new CustomEvent("wies:org-selection-applied", {
          detail: { rows: selectedOrgs() },
        }),
      );
      var sheet = document.getElementById("assignment-org-modal");
      if (sheet && sheet.hide) sheet.hide();
    });
  }

  var selectionsEl = document.getElementById(
    "assignment-org-current-selections",
  );
  var currentSelections = selectionsEl
    ? JSON.parse(selectionsEl.textContent)
    : {};
  if (Object.keys(currentSelections).length > 0) {
    treeState.restoreSelections(currentSelections);
    tree.sync();
    rebuildSelectionList();
    for (var nodeId in currentSelections) {
      tree.expandAncestorsOf(nodeId);
    }
  }
})();
