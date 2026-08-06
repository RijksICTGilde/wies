(function () {
  "use strict";

  var dataEl = document.getElementById("client-data");
  var data = dataEl ? JSON.parse(dataEl.textContent) : [];
  var container = document.getElementById("client-tree-container");
  var searchInput = document.getElementById("client-search");
  var applyBtn = document.getElementById("client-apply-btn");

  if (!container) return;

  // No collapse-to-parent: clicking a child records THAT child as the selection,
  // even when it is the only child of its parent. A parent still lights up via
  // cascade, but the token/filter stays on what you clicked — matching the older
  // behaviour the filter is meant to have.
  var treeState = new TreeState(data, { collapseToParent: false });
  var tree = new WiesOrgTree({
    state: treeState,
    container: container,
    accessibleLabel: "Opdrachtgevers",
    onToggle: rebuildSelectionList,
  });
  tree.render().bindSearch(searchInput);

  /** The filter form listens with `change from:[data-filter-input]`, so the event
   *  must originate on one of those inputs; dispatching it on the form is a no-op. */
  function dispatchFilterChange(form) {
    var sentinel = form.querySelector("[data-filter-input]");
    (sentinel || form).dispatchEvent(new Event("change", { bubbles: true }));
  }

  // Above this many the tokens stop helping: they push the CTA off-screen and
  // nobody reads a wall of chips. The count in the button says the same thing.
  var MAX_VISIBLE_TOKENS = 6;

  /** The button says what it is about to apply. With nothing selected there is
   *  no filter to name — and "Wis filter" would be a lie when there was none to
   *  begin with — so the neutral wording is the honest one. */
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
      // The form listens with `change from:[data-filter-input]`, so the event has
      // to come FROM such an element — triggering it on the form matches nothing.
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
    // Open towards what is actually selected — after the collapse in
    // restoreSelections that can be a parent rather than the stored children.
    for (var entry of treeState.explicitSelections) {
      tree.expandAncestorsOf(entry[0]);
    }
  }
})();
