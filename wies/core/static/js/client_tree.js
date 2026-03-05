(function () {
  "use strict";

  var dataEl = document.getElementById("client-data");
  var data = dataEl ? JSON.parse(dataEl.textContent) : [];
  var container = document.getElementById("client-tree-container");
  var selectionList = document.getElementById("client-selection-list");
  var searchInput = document.getElementById("client-search");
  var clearBtn = document.getElementById("client-clear-btn");
  var applyBtn = document.getElementById("client-apply-btn");

  if (!container) return;

  var treeState = new TreeState(data);

  // nodeId (string) → DOM <li> element, for efficient DOM lookups
  var domNodes = new Map();

  // ============================================================
  // TREE BUILDING
  // ============================================================

  function buildTree(node) {
    var li = document.createElement("li");
    li.className =
      "client-tree-node" +
      (node.children && node.children.length ? " has-children" : "") +
      (node.self ? " self-node" : "");
    li.dataset.nodeId = String(node.id);
    domNodes.set(String(node.id), li);

    // Fold/expand toggle
    if (node.children && node.children.length) {
      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "client-toggle";
      toggle.textContent = "›";
      toggle.title = "Uitklappen/inklappen";
      toggle.setAttribute("aria-label", "Uitklappen/inklappen");
      toggle.addEventListener("click", function () {
        li.classList.toggle("collapsed");
      });
      li.appendChild(toggle);
    } else {
      var spacer = document.createElement("span");
      spacer.className = "client-toggle-spacer";
      li.appendChild(spacer);
    }

    var checkboxId = "client-node-" + String(node.id);
    var label = document.createElement("label");
    label.htmlFor = checkboxId;

    var checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = checkboxId;
    checkbox.addEventListener("change", function () {
      if (checkbox.checked) {
        treeState.check(node.id);
      } else {
        treeState.uncheck(node.id);
      }
      syncAllDOM();
      // Expand on check so children become visible
      if (checkbox.checked && li.classList.contains("has-children")) {
        li.classList.remove("collapsed");
      }
    });
    label.appendChild(checkbox);

    var displayText = node.self
      ? 'Direct onder "' + node.label + '"'
      : node.label;
    var labelText = document.createTextNode(displayText);
    label.appendChild(labelText);

    if (node.nr_of_placements !== undefined) {
      var badge = document.createElement("span");
      badge.className = "client-placement-badge";
      badge.textContent = node.nr_of_placements;
      label.appendChild(badge);
    }

    li.appendChild(label);

    if (node.children && node.children.length) {
      var childUl = document.createElement("ul");
      childUl.className = "client-tree-level";
      for (var i = 0; i < node.children.length; i++) {
        childUl.appendChild(buildTree(node.children[i]));
      }
      li.appendChild(childUl);
    }

    return li;
  }

  // ============================================================
  // DOM SYNC — read state from TreeState, write to DOM
  // ============================================================

  function syncAllDOM() {
    treeState.nodes.forEach(function (node) {
      var li = domNodes.get(node.id);
      if (!li) return;
      var cb = li.querySelector(":scope > label > input[type='checkbox']");
      if (cb) {
        cb.checked = node.checked;
        cb.indeterminate = node.indeterminate;
      }
    });
    updateHighlightClasses();
    rebuildSelectionList();
    updateResultsCount();
  }

  function updateResultsCount() {
    var resultsEl = document.getElementById("client-results-count");
    if (!resultsEl) return;
    // Sum placements from explicitly selected nodes
    var total = 0;
    treeState.explicitSelections.forEach(function (label, nodeId) {
      var node = treeState.getNode(nodeId);
      if (node && node.nr_of_placements !== undefined) {
        total += node.nr_of_placements;
      }
    });
    resultsEl.textContent = total > 0 ? total + " plaatsingen" : "";
  }

  function updateHighlightClasses() {
    domNodes.forEach(function (li, nodeId) {
      var isExplicit = treeState.explicitSelections.has(nodeId);
      li.classList.toggle("checked", isExplicit);
    });
  }

  // ============================================================
  // SELECTION PANEL
  // ============================================================

  function rebuildSelectionList() {
    selectionList.innerHTML = "";

    // Update count badge
    var countEl = document.getElementById("client-selection-count");
    if (countEl) {
      var count = treeState.explicitSelections.size;
      countEl.textContent = count;
      countEl.style.display = count > 0 ? "" : "none";
    }

    if (treeState.explicitSelections.size === 0) {
      var empty = document.createElement("li");
      empty.className = "client-modal__empty-state";
      empty.textContent = "Niets geselecteerd";
      selectionList.appendChild(empty);
    } else {
      for (var entry of treeState.explicitSelections) {
        var nodeId = entry[0];
        var text = entry[1];
        var li = document.createElement("li");
        li.className = "client-modal__selection-item";
        var span = document.createElement("span");
        span.textContent = text;
        span.title = text;
        li.appendChild(span);
        var removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "client-modal__selection-remove";
        removeBtn.setAttribute("aria-label", "Verwijder " + text);
        removeBtn.textContent = "×";
        removeBtn.addEventListener(
          "click",
          (function (id) {
            return function () {
              treeState.removeSelection(id);
              syncAllDOM();
            };
          })(nodeId),
        );
        li.appendChild(removeBtn);
        selectionList.appendChild(li);
      }
    }
  }

  // ============================================================
  // SEARCH FILTERING — tree mode
  // ============================================================

  function filterTree(query) {
    var q = query.toLowerCase().trim();

    if (!q) {
      // Show all nodes, restore collapsed state
      domNodes.forEach(function (li) {
        li.classList.remove("search-hidden");
        li.classList.remove("search-match");
      });
      container
        .querySelectorAll("li.client-tree-node.has-children")
        .forEach(function (li) {
          li.classList.add("collapsed");
        });
      updateResultsCount();
      return;
    }

    // Hide all nodes and uncollapse everything (visibility controlled by search-hidden only)
    domNodes.forEach(function (li) {
      li.classList.add("search-hidden");
      li.classList.remove("search-match");
      li.classList.remove("collapsed");
    });

    // Find matching nodes and mark them + their ancestors visible
    treeState.nodes.forEach(function (node) {
      var matches = false;
      if (node.label && node.label.toLowerCase().includes(q)) matches = true;
      if (!matches && node.abbreviations) {
        for (var i = 0; i < node.abbreviations.length; i++) {
          if (node.abbreviations[i].toLowerCase().includes(q)) {
            matches = true;
            break;
          }
        }
      }
      if (matches) {
        var li = domNodes.get(node.id);
        if (li) {
          li.classList.remove("search-hidden");
          li.classList.add("search-match");
        }
        // Show ancestors
        var ancestor = node.parent;
        while (ancestor) {
          var ancestorLi = domNodes.get(ancestor.id);
          if (ancestorLi) {
            ancestorLi.classList.remove("search-hidden");
          }
          ancestor = ancestor.parent;
        }
      }
    });
    updateResultsCount();
  }

  // ============================================================
  // EVENT LISTENERS
  // ============================================================

  if (searchInput) {
    var debounceTimer;
    searchInput.addEventListener("input", function () {
      var value = this.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        filterTree(value);
      }, 300);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      treeState.clearAll();
      syncAllDOM();

      var orgInputsContainer = document.getElementById("org-filter-inputs");
      var sidebarForm = document.querySelector(".filter-sidebar-form");
      if (orgInputsContainer) orgInputsContainer.innerHTML = "";

      var dialog = document.getElementById("clientModal");
      if (dialog) dialog.close();

      updateOrgFilterButtonText();
      if (sidebarForm) htmx.trigger(sidebarForm, "change");
    });
  }

  if (applyBtn) {
    applyBtn.addEventListener("click", function () {
      var orgInputsContainer = document.getElementById("org-filter-inputs");
      var sidebarForm = document.querySelector(".filter-sidebar-form");
      if (orgInputsContainer) {
        orgInputsContainer.innerHTML = "";
        for (var entry of treeState.explicitSelections) {
          var nodeId = entry[0];
          var input = document.createElement("input");
          input.type = "hidden";
          input.dataset.filterInput = "";
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
    });
  }

  // ============================================================
  // RENDER TREE
  // ============================================================

  var rootUl = document.createElement("ul");
  rootUl.className = "client-tree-level";

  for (var i = 0; i < data.length; i++) {
    rootUl.appendChild(buildTree(data[i]));
  }

  container.appendChild(rootUl);

  // Start fully collapsed
  container
    .querySelectorAll("li.client-tree-node.has-children")
    .forEach(function (li) {
      li.classList.add("collapsed");
    });

  // Restore selections from current query params
  var selectionsEl = document.getElementById("client-current-selections");
  var currentSelections = selectionsEl
    ? JSON.parse(selectionsEl.textContent)
    : {};
  if (Object.keys(currentSelections).length > 0) {
    treeState.restoreSelections(currentSelections);
    syncAllDOM();
    // Expand ancestors of selected nodes so they're visible
    for (var nodeId in currentSelections) {
      var li = domNodes.get(nodeId);
      if (li) {
        var ancestor = li.parentElement && li.parentElement.parentElement;
        while (ancestor && ancestor.classList.contains("client-tree-node")) {
          ancestor.classList.remove("collapsed");
          ancestor =
            ancestor.parentElement && ancestor.parentElement.parentElement;
        }
      }
    }
  }
})();
