(function () {
  "use strict";

  var dataEl = document.getElementById("assignment-org-data");
  var data = dataEl ? JSON.parse(dataEl.textContent) : [];
  var container = document.getElementById("assignment-org-tree-container");
  var searchInput = document.getElementById("assignment-org-search");
  var applyBtn = document.getElementById("assignment-org-apply-btn");

  if (!container) return;

  // An assignment is linked to concrete organisations. A nested type folder
  // under a ministry ("Agentschappen van BZK") carries no organisation of its
  // own, but IS selectable: ticking it selects the organisations in it.
  var treeState = new TreeState(data, {
    collapseToParent: false,
    // Ticking a type folder selects the concrete orgs under it, and the
    // selection (and grey fill) lands on those orgs, not the folder.
    groupSelectsChildren: true,
  });
  var tree = new WiesOrgTree({
    state: treeState,
    container: container,
    showCounts: false,
    accessibleLabel: "Opdrachtgevers",
    // Only the nested folders are selectable: a top-level type folder
    // ("Gemeenten") would link hundreds of orgs in one click. A "self" helper
    // node carries no distinct organisation, so it stays structure-only.
    isSelectable: function (node) {
      return !node.self && (!node.group || node.nested);
    },
    onToggle: rebuildSelectionList,
  });
  tree.render().bindSearch(searchInput);

  // Above this many, the tokens push the CTA off-screen; the button's count
  // says the same thing.
  var MAX_VISIBLE_TOKENS = 6;

  // Group and self nodes carry no organisation, so they never reach the form;
  // groupSelectsChildren already moved a folder's selection onto its orgs.
  function selectedOrgs() {
    var rows = [];
    treeState.explicitSelections.forEach(function (label, nodeId) {
      var node = treeState.getNode(nodeId);
      if (node && (node.group || node.self)) return;
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
