(function () {
  "use strict";

  var dataEl = document.getElementById("client-data");
  var data = dataEl ? JSON.parse(dataEl.textContent) : [];
  var container = document.getElementById("client-tree-container");
  var searchInput = document.getElementById("client-search");
  var applyBtn = document.getElementById("client-apply-btn");

  if (!container) return;

  // No collapse-to-parent: the filter stays on the node you clicked, even when
  // it is its parent's only child.
  var treeState = new TreeState(data, { collapseToParent: false });
  var tree = new WiesOrgTree({
    state: treeState,
    container: container,
    accessibleLabel: "Opdrachtgevers",
    onToggle: rebuildSelectionList,
  });
  tree.render().bindSearch(searchInput);

  // The form listens with `change from:[data-filter-input]`, so the event must
  // originate on such an input; dispatching it on the form is a no-op.
  function dispatchFilterChange(form) {
    var sentinel = form.querySelector("[data-filter-input]");
    (sentinel || form).dispatchEvent(new Event("change", { bubbles: true }));
  }

  // Above this many, the tokens push the CTA off-screen; the button's count
  // says the same thing.
  var MAX_VISIBLE_TOKENS = 6;

  function updateApplyLabel() {
    if (!applyBtn) return;
    var n = treeState.explicitSelections.size;
    var text = "Pas toe";
    if (n === 1) text = "Pas filter toe";
    else if (n > 1) text = "Pas " + n + " filters toe";
    applyBtn.setAttribute("text", text);
  }

  function rebuildSelectionList() {
    updateApplyLabel();
    var box = document.getElementById("client-selection-tokens");
    if (!box) return;
    box.innerHTML = "";
    var count = treeState.explicitSelections.size;
    box.hidden = count === 0 || count > MAX_VISIBLE_TOKENS;
    if (box.hidden) return;
    for (var entry of treeState.explicitSelections) {
      var nodeId = entry[0];
      var text = entry[1];
      var token = document.createElement("nldd-token");
      token.setAttribute("control", "dismiss");
      token.setAttribute("dismiss-text", "Verwijder " + text);
      token.textContent = text;
      token.addEventListener(
        "dismiss",
        (function (id) {
          return function () {
            treeState.removeSelection(id);
            tree.sync();
            rebuildSelectionList();
          };
        })(nodeId),
      );
      box.appendChild(token);
    }
  }

  if (applyBtn) {
    applyBtn.addEventListener("click", function () {
      var orgInputsContainer = document.getElementById("org-filter-inputs");
      var sidebarForm = document.getElementById("filter-form");
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

      var sheet = document.getElementById("client-modal");
      if (sheet && sheet.hide) sheet.hide();

      // The sidebar quick options re-render via the filter form's OOB swap.
      if (sidebarForm) dispatchFilterChange(sidebarForm);
    });
  }

  var selectionsEl = document.getElementById("client-current-selections");
  var currentSelections = selectionsEl
    ? JSON.parse(selectionsEl.textContent)
    : {};
  if (Object.keys(currentSelections).length > 0) {
    treeState.restoreSelections(currentSelections);
    tree.sync();
    rebuildSelectionList();
    // After the collapse in restoreSelections this can be a parent rather than
    // the stored children.
    for (var entry of treeState.explicitSelections) {
      tree.expandAncestorsOf(entry[0]);
    }
  }
})();
