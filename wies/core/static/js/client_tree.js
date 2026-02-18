(function () {
  "use strict";

  const dataEl = document.getElementById("client-data");
  const data = dataEl ? JSON.parse(dataEl.textContent) : [];
  const container = document.getElementById("client-tree-container");
  const selectionList = document.getElementById("client-selection-list");
  const searchInput = document.getElementById("client-search");
  const clearBtn = document.getElementById("client-clear-btn");
  const applyBtn = document.getElementById("client-apply-btn");

  if (!container) return;

  // nodeId (string) → label text for nodes the user explicitly clicked
  const explicitSelections = new Map();

  // ============================================================
  // TREE BUILDING
  // ============================================================

  function buildTree(node) {
    const li = document.createElement("li");
    li.className =
      "client-tree-node" +
      (node.children && node.children.length ? " has-children" : "") +
      (node.self ? " self-node" : "");
    li.dataset.nodeId = String(node.id);

    // Fold/expand toggle (before the label, outside it so clicks don't toggle checkbox)
    if (node.children && node.children.length) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "client-toggle";
      toggle.textContent = "▼";
      toggle.title = "Uitklappen/inklappen";
      toggle.setAttribute("aria-label", "Uitklappen/inklappen");
      toggle.addEventListener("click", function () {
        li.classList.toggle("collapsed");
      });
      li.appendChild(toggle);
    } else {
      const spacer = document.createElement("span");
      spacer.className = "client-toggle-spacer";
      li.appendChild(spacer);
    }

    const checkboxId = "client-node-" + String(node.id);
    const label = document.createElement("label");
    label.htmlFor = checkboxId;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = checkboxId;
    checkbox.addEventListener("change", function () {
      onCheckboxChange(li, checkbox);
    });
    label.appendChild(checkbox);

    const labelText = document.createTextNode(node.label);
    label.appendChild(labelText);

    // Placement count badge
    if (node.nr_of_placements !== undefined) {
      const badge = document.createElement("span");
      badge.className = "client-placement-badge";
      badge.textContent = node.nr_of_placements;
      label.appendChild(badge);
    }

    li.appendChild(label);

    // Recursively add children
    if (node.children && node.children.length) {
      const childUl = document.createElement("ul");
      childUl.className = "client-tree-level";

      for (const child of node.children) {
        childUl.appendChild(buildTree(child));
      }

      li.appendChild(childUl);
    }

    return li;
  }

  // ============================================================
  // CHECKBOX CASCADE
  // ============================================================

  function getNodeLabel(li) {
    const labelEl = li.querySelector(":scope > label");
    let text = "";
    for (const child of labelEl.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) text += child.textContent;
    }
    text = text.trim();
    if (li.classList.contains("self-node")) text += " (direct)";
    return text;
  }

  function onCheckboxChange(li, checkbox) {
    const nodeId = li.dataset.nodeId;
    cascadeDown(li, checkbox.checked);
    cascadeUp(li);
    if (checkbox.checked) {
      // Add this node as explicit selection, remove any descendants that are now implied
      explicitSelections.set(nodeId, getNodeLabel(li));
      li.querySelectorAll("li.client-tree-node").forEach(function (desc) {
        explicitSelections.delete(desc.dataset.nodeId);
      });
    } else {
      explicitSelections.delete(nodeId);
      // Remove any descendants that were previously explicit
      li.querySelectorAll("li.client-tree-node").forEach(function (desc) {
        explicitSelections.delete(desc.dataset.nodeId);
      });
      // Demote any ancestors that were explicit: replace them with their
      // still-checked children (excluding the subtree we just unchecked)
      demoteAncestors(li);
    }
    // Expand on check so children become visible
    if (checkbox.checked && li.classList.contains("has-children")) {
      li.classList.remove("collapsed");
    }
    rebuildSelectionList();
    updateHighlightClasses();
  }

  function cascadeDown(li, checked) {
    const descendants = li.querySelectorAll('input[type="checkbox"]');
    descendants.forEach(function (cb) {
      cb.checked = checked;
      cb.indeterminate = false;
    });
  }

  function cascadeUp(startLi) {
    let currentLi = startLi;

    while (currentLi) {
      const parentUl = currentLi.parentElement;
      if (!parentUl) break;
      const parentLi = parentUl.parentElement;
      if (!parentLi || !parentLi.classList.contains("client-tree-node")) break;

      const parentCheckbox = parentLi.querySelector(
        ":scope > label > input[type='checkbox']",
      );
      if (!parentCheckbox) break;

      const childUl = parentLi.querySelector(":scope > ul.client-tree-level");
      if (!childUl) break;

      const childCheckboxes = [];
      for (const childLi of childUl.children) {
        const cb = childLi.querySelector(
          ":scope > label > input[type='checkbox']",
        );
        if (cb) childCheckboxes.push(cb);
      }

      const allChecked =
        childCheckboxes.length > 0 &&
        childCheckboxes.every(function (cb) {
          return cb.checked;
        });
      const someChecked = childCheckboxes.some(function (cb) {
        return cb.checked || cb.indeterminate;
      });

      if (allChecked) {
        parentCheckbox.checked = true;
        parentCheckbox.indeterminate = false;
      } else if (someChecked) {
        parentCheckbox.checked = false;
        parentCheckbox.indeterminate = true;
      } else {
        parentCheckbox.checked = false;
        parentCheckbox.indeterminate = false;
      }

      currentLi = parentLi;
    }
  }

  // Promote all checked/indeterminate direct children of a li as explicit selections.
  // Fully-checked children become explicit directly; indeterminate children are recursed into.
  function promoteCheckedChildren(parentLi) {
    const childUl = parentLi.querySelector(":scope > ul.client-tree-level");
    if (!childUl) return;
    for (const childLi of childUl.querySelectorAll(
      ":scope > li.client-tree-node",
    )) {
      const childCb = childLi.querySelector(
        ":scope > label > input[type='checkbox']",
      );
      if (!childCb) continue;
      if (childCb.checked && !childCb.indeterminate) {
        explicitSelections.set(childLi.dataset.nodeId, getNodeLabel(childLi));
      } else if (childCb.indeterminate) {
        promoteCheckedChildren(childLi);
      }
    }
  }

  // When a node is unchecked, walk up and demote any ancestor that was explicit.
  function demoteAncestors(uncheckedLi) {
    let current = uncheckedLi;
    while (current) {
      const parentUl = current.parentElement;
      if (!parentUl) break;
      const parentLi = parentUl.parentElement;
      if (!parentLi || !parentLi.classList.contains("client-tree-node")) break;

      const parentId = parentLi.dataset.nodeId;
      if (explicitSelections.has(parentId)) {
        explicitSelections.delete(parentId);
        promoteCheckedChildren(parentLi);
      }
      current = parentLi;
    }
  }

  // ============================================================
  // HIGHLIGHT: mark explicitly selected nodes
  // ============================================================

  function updateHighlightClasses() {
    container.querySelectorAll("li.client-tree-node").forEach(function (li) {
      if (explicitSelections.has(li.dataset.nodeId)) {
        li.classList.add("checked");
      } else {
        li.classList.remove("checked");
      }
    });
  }

  // ============================================================
  // SELECTION PANEL
  // Shows explicitly clicked nodes.
  // ============================================================

  function rebuildSelectionList() {
    selectionList.innerHTML = "";
    if (explicitSelections.size === 0) {
      const empty = document.createElement("li");
      empty.className = "client-modal__empty-state";
      empty.textContent = "Niets geselecteerd";
      selectionList.appendChild(empty);
    } else {
      for (const [nodeId, text] of explicitSelections) {
        const li = document.createElement("li");
        li.className = "client-modal__selection-item";
        const span = document.createElement("span");
        span.textContent = text;
        li.appendChild(span);
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "client-modal__selection-remove";
        removeBtn.setAttribute("aria-label", `Verwijder ${text}`);
        removeBtn.textContent = "×";
        removeBtn.addEventListener("click", function () {
          removeExplicitSelection(nodeId);
        });
        li.appendChild(removeBtn);
        selectionList.appendChild(li);
      }
    }
  }

  // ============================================================
  // SEARCH FILTERING — flat list mode
  // ============================================================

  let flatList = null;

  function nodeMatches(node, q) {
    if (node.label && node.label.toLowerCase().includes(q)) return true;
    if (node.abbreviations) {
      for (const abbr of node.abbreviations) {
        if (abbr.toLowerCase().includes(q)) return true;
      }
    }
    return false;
  }

  function collectMatches(nodes, q, result) {
    for (const node of nodes) {
      // Group nodes are structural containers (e.g. ministry headers) and not
      // selectable themselves, so we skip them even if their name matches.
      // Self-nodes are duplicates of their parent shown for "direct placements
      // only" filtering; skip them too — the parent already appears in results.
      // Their children are still searched recursively.
      if (!node.group && !node.self && nodeMatches(node, q)) result.push(node);
      if (node.children) collectMatches(node.children, q, result);
    }
  }

  function isCheckedInTree(nodeId) {
    const treeLi = container.querySelector(
      `li[data-node-id="${String(nodeId)}"]`,
    );
    if (!treeLi) return false;
    const cb = treeLi.querySelector(":scope > label > input[type='checkbox']");
    return cb ? cb.checked : false;
  }

  function renderFlatList(matches) {
    if (flatList) flatList.remove();
    flatList = document.createElement("ul");
    flatList.id = "client-flat-list";
    flatList.className = "client-flat-list";

    if (matches.length === 0) {
      const empty = document.createElement("li");
      empty.className = "client-modal__empty-state";
      empty.textContent = "Geen resultaten";
      flatList.appendChild(empty);
    } else {
      for (const node of matches) {
        const li = document.createElement("li");
        const label = document.createElement("label");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = isCheckedInTree(node.id);
        checkbox.dataset.nodeId = String(node.id);
        checkbox.addEventListener("change", function () {
          syncToTree(node.id, checkbox.checked);
        });
        if (explicitSelections.has(String(node.id))) {
          li.classList.add("explicit");
        }
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(node.label));
        if (node.abbreviations && node.abbreviations.length) {
          const abbr = document.createElement("span");
          abbr.className = "client-abbreviation";
          abbr.textContent = node.abbreviations[0];
          label.appendChild(abbr);
        }
        li.appendChild(label);
        flatList.appendChild(li);
      }
    }

    container.appendChild(flatList);
  }

  // Used by flat list checkboxes — full cascade down + up
  function syncToTree(nodeId, checked) {
    const nodeIdStr = String(nodeId);
    const treeLi = container.querySelector(`li[data-node-id="${nodeIdStr}"]`);
    if (!treeLi) return;
    const cb = treeLi.querySelector(":scope > label > input[type='checkbox']");
    if (!cb) return;
    cb.checked = checked;
    cascadeDown(treeLi, checked);
    cascadeUp(treeLi);
    if (checked) {
      explicitSelections.set(nodeIdStr, getNodeLabel(treeLi));
      treeLi.querySelectorAll("li.client-tree-node").forEach(function (desc) {
        explicitSelections.delete(desc.dataset.nodeId);
      });
    } else {
      explicitSelections.delete(nodeIdStr);
      treeLi.querySelectorAll("li.client-tree-node").forEach(function (desc) {
        explicitSelections.delete(desc.dataset.nodeId);
      });
      demoteAncestors(treeLi);
    }
    // Also update the flat list item if it's currently visible
    if (flatList) {
      flatList
        .querySelectorAll("input[type='checkbox']")
        .forEach(function (flatCb) {
          if (flatCb.dataset.nodeId === nodeIdStr) {
            flatCb.checked = checked;
            flatCb
              .closest("li")
              .classList.toggle("explicit", explicitSelections.has(nodeIdStr));
          }
        });
    }
    rebuildSelectionList();
    updateHighlightClasses();
  }

  // Used by × button — fully removes this selection: uncheck node and all descendants
  function removeExplicitSelection(nodeId) {
    const nodeIdStr = String(nodeId);
    explicitSelections.delete(nodeIdStr);
    const treeLi = container.querySelector(`li[data-node-id="${nodeIdStr}"]`);
    if (treeLi) {
      // Uncheck this node and all descendants, clear any explicit selections under it
      cascadeDown(treeLi, false);
      treeLi.querySelectorAll("li.client-tree-node").forEach(function (desc) {
        explicitSelections.delete(desc.dataset.nodeId);
      });
      cascadeUp(treeLi);
    }
    rebuildSelectionList();
    updateHighlightClasses();
  }

  function filterTree(query) {
    const q = query.toLowerCase().trim();
    const rootUl = container.querySelector(":scope > ul.client-tree-level");

    if (!q) {
      if (rootUl) rootUl.style.display = "";
      if (flatList) {
        flatList.remove();
        flatList = null;
      }
      return;
    }

    if (rootUl) rootUl.style.display = "none";
    const matches = [];
    collectMatches(data, q, matches);
    renderFlatList(matches);
  }

  // ============================================================
  // EVENT LISTENERS
  // ============================================================

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      filterTree(this.value);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      container
        .querySelectorAll('input[type="checkbox"]')
        .forEach(function (cb) {
          cb.checked = false;
          cb.indeterminate = false;
        });
      container.querySelectorAll("li.client-tree-node").forEach(function (li) {
        li.classList.remove("checked");
      });
      explicitSelections.clear();
      rebuildSelectionList();
    });
  }

  if (applyBtn) {
    applyBtn.addEventListener("click", function () {
      // Write explicit selections as hidden inputs into the sidebar form
      const orgInputsContainer = document.getElementById("org-filter-inputs");
      const sidebarForm = document.querySelector(".filter-sidebar-form");
      if (orgInputsContainer) {
        orgInputsContainer.innerHTML = "";
        for (const [nodeId] of explicitSelections) {
          const input = document.createElement("input");
          input.type = "hidden";
          input.dataset.filterInput = "";
          if (nodeId.startsWith("self-")) {
            input.name = "org_self";
            input.value = nodeId.slice(5); // strip "self-"
          } else if (nodeId.startsWith("group-")) {
            input.name = "org_type";
            input.value = nodeId.slice(6); // strip "group-"
          } else {
            input.name = "org";
            input.value = nodeId;
          }
          orgInputsContainer.appendChild(input);
        }
      }

      const dialog = document.getElementById("clientModal");
      if (dialog) dialog.close();

      // Trigger the sidebar form HTMX request to apply the filter
      if (sidebarForm) {
        htmx.trigger(sidebarForm, "change");
      }
    });
  }

  // ============================================================
  // RENDER TREE
  // ============================================================

  const rootUl = document.createElement("ul");
  rootUl.className = "client-tree-level";

  for (const child of data) {
    rootUl.appendChild(buildTree(child));
  }

  container.appendChild(rootUl);

  // Start fully collapsed
  container
    .querySelectorAll("li.client-tree-node.has-children")
    .forEach(function (li) {
      li.classList.add("collapsed");
    });

  // Restore selections from current query params (passed by server on modal open)
  const selectionsEl = document.getElementById("client-current-selections");
  const currentSelections = selectionsEl
    ? JSON.parse(selectionsEl.textContent)
    : {};
  if (Object.keys(currentSelections).length > 0) {
    for (const [nodeId, label] of Object.entries(currentSelections)) {
      const treeLi = container.querySelector(`li[data-node-id="${nodeId}"]`);
      if (treeLi) {
        const cb = treeLi.querySelector(
          ":scope > label > input[type='checkbox']",
        );
        if (cb) {
          cb.checked = true;
          cascadeDown(treeLi, true);
          cascadeUp(treeLi);
          // Expand ancestors so selected node is visible
          let ancestor =
            treeLi.parentElement && treeLi.parentElement.parentElement;
          while (ancestor && ancestor.classList.contains("client-tree-node")) {
            ancestor.classList.remove("collapsed");
            ancestor =
              ancestor.parentElement && ancestor.parentElement.parentElement;
          }
        }
      }
      explicitSelections.set(nodeId, label);
    }
    rebuildSelectionList();
    updateHighlightClasses();
  }
})();
