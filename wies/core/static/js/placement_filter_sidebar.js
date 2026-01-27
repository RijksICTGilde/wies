// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function () {
  // ============================================================================
  // FILTER MANAGEMENT FUNCTIONS
  // ============================================================================

  function removeFilter(filterName, filterType, filterValue) {
    const form = document.querySelector(".filter-sidebar-form");
    if (!form) return;

    if (filterType === "zoek") {
      const searchInput = document.querySelector("#search");
      if (searchInput) {
        searchInput.value = "";
      }
    } else if (filterType === "select") {
      const selectElement = form.querySelector(`[name="${filterName}"]`);
      if (selectElement) {
        selectElement.selectedIndex = 0;
      }
    } else if (filterType === "select-multi") {
      // For multi-select (label filters), find the correct dropdown
      // There are multiple <select name="label"> elements (one per category)
      const selectElements = form.querySelectorAll(`[name="${filterName}"]`);
      selectElements.forEach((selectElement) => {
        for (let i = 0; i < selectElement.options.length; i++) {
          if (selectElement.options[i].value === filterValue) {
            selectElement.selectedIndex = 0;
            return;
          }
        }
      });
    } else if (filterType === "date_range") {
      const fromInput = document.getElementById(`filter-${filterName}-from`);
      const toInput = document.getElementById(`filter-${filterName}-to`);
      const hiddenInput = document.getElementById(
        `filter-${filterName}-combined`,
      );
      const validationMessage = document.getElementById(
        `${filterName}-validation-message`,
      );

      if (fromInput) fromInput.value = "";
      if (toInput) toInput.value = "";
      if (hiddenInput) hiddenInput.value = "";
      if (validationMessage) validationMessage.style.display = "none";
    } else if (filterType === "tree-multi") {
      // For tree multi-select, remove the specific hidden input
      const container = document.getElementById("org-tree-selected-inputs");
      if (container) {
        const input = container.querySelector(`input[value="${filterValue}"]`);
        if (input) {
          input.remove();
        }
      }
    }

    // Trigger HTMX form submission
    htmx.trigger(form, "change");
  }

  // ============================================================================
  // EVENT DELEGATION - All click handlers
  // ============================================================================

  document.addEventListener("click", function (e) {
    // Filter chip removal
    if (e.target.closest(".filter-chip-remove")) {
      e.preventDefault();
      const button = e.target.closest(".filter-chip-remove");
      const filterName = button.dataset.filterName;
      const filterValue = button.dataset.filterValue;
      const chip = button.closest(".filter-chip");
      const filterType = chip.dataset.filterType;

      removeFilter(filterName, filterType, filterValue);
    }
  });

  // ============================================================================
  // ORGANIZATION TREE FILTER
  // ============================================================================

  // Make these functions globally accessible for inline event handlers
  window.handleOrgTreeCheckboxChange = function (checkbox) {
    const isChecked = checkbox.checked;
    const treeNode = checkbox.closest(".org-tree-node");

    // Clear indeterminate state when explicitly clicked
    checkbox.indeterminate = false;

    // If node has children and is expanded, update all descendant checkboxes
    if (treeNode) {
      const childCheckboxes = treeNode.querySelectorAll(
        ".org-tree-node__children .org-tree-node__checkbox",
      );
      childCheckboxes.forEach((childCb) => {
        childCb.checked = isChecked;
        childCb.indeterminate = false;
      });
    }

    // Update parent checkbox states (tri-state)
    updateParentCheckboxStates(treeNode);

    // Update hidden inputs
    updateOrgTreeSelectedInputs();

    // Trigger filter update
    triggerOrgFilterUpdate();
  };

  // Update parent checkboxes to reflect children's state (tri-state logic)
  function updateParentCheckboxStates(startNode) {
    if (!startNode) return;

    let currentNode = startNode.parentElement?.closest(".org-tree-node");

    while (currentNode) {
      const parentCheckbox = currentNode.querySelector(
        ":scope > .org-tree-node__header .org-tree-node__checkbox",
      );
      const childrenContainer = currentNode.querySelector(
        ":scope > .org-tree-node__children",
      );

      if (parentCheckbox && childrenContainer) {
        const childCheckboxes = childrenContainer.querySelectorAll(
          ".org-tree-node__checkbox",
        );

        if (childCheckboxes.length > 0) {
          const checkedCount = Array.from(childCheckboxes).filter(
            (cb) => cb.checked,
          ).length;
          const indeterminateCount = Array.from(childCheckboxes).filter(
            (cb) => cb.indeterminate,
          ).length;

          if (checkedCount === 0 && indeterminateCount === 0) {
            // No children checked
            parentCheckbox.checked = false;
            parentCheckbox.indeterminate = false;
          } else if (
            checkedCount === childCheckboxes.length &&
            indeterminateCount === 0
          ) {
            // All children checked
            parentCheckbox.checked = true;
            parentCheckbox.indeterminate = false;
          } else {
            // Some children checked (partial selection)
            parentCheckbox.checked = false;
            parentCheckbox.indeterminate = true;
          }
        }
      }

      // Move up to next parent
      currentNode = currentNode.parentElement?.closest(".org-tree-node");
    }
  }

  // Collapse all expanded org tree nodes
  window.collapseAllOrgTreeNodes = function () {
    const expandedNodes = document.querySelectorAll(
      '.org-tree-filter .org-tree-node[aria-expanded="true"]',
    );
    expandedNodes.forEach((node) => {
      node.setAttribute("aria-expanded", "false");
      const toggle = node.querySelector(".org-tree-node__toggle");
      if (toggle) {
        toggle.classList.remove("org-tree-node__toggle--expanded");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  };

  // Select all visible org tree nodes
  window.selectAllOrgTreeNodes = function () {
    const checkboxes = document.querySelectorAll(
      ".org-tree-filter .org-tree-node__checkbox",
    );
    checkboxes.forEach((cb) => {
      cb.checked = true;
      cb.indeterminate = false;
    });
    updateOrgTreeSelectedInputs();
    triggerOrgFilterUpdate();
  };

  // Deselect all org tree nodes
  window.deselectAllOrgTreeNodes = function () {
    const checkboxes = document.querySelectorAll(
      ".org-tree-filter .org-tree-node__checkbox",
    );
    checkboxes.forEach((cb) => {
      cb.checked = false;
      cb.indeterminate = false;
    });
    updateOrgTreeSelectedInputs();
    triggerOrgFilterUpdate();
  };

  window.selectOrgFromSearch = function (element, orgId, shouldSelect) {
    const checkbox = element.querySelector('input[type="checkbox"]');
    if (checkbox) {
      checkbox.checked = shouldSelect;
    }

    // Check if we're in the modal or sidebar context
    const isInModal = element.closest("#org-filter-modal");

    if (isInModal) {
      // Modal context: update modal tree and selection panel
      const modalTreeCheckbox = document.querySelector(
        `#org-filter-modal .org-tree-node__checkbox[value="${orgId}"]`,
      );
      if (modalTreeCheckbox) {
        modalTreeCheckbox.checked = shouldSelect;
        const treeNode = modalTreeCheckbox.closest(".org-tree-node");
        updateModalParentCheckboxStates(treeNode);
      }
      updateOrgModalSelection();

      // Clear modal search results
      const searchResults = document.getElementById("org-modal-search-results");
      if (searchResults) {
        searchResults.innerHTML = "";
      }
    } else {
      // Sidebar context: update sidebar tree and trigger filter
      const treeCheckbox = document.querySelector(
        `.org-tree-node__checkbox[value="${orgId}"]`,
      );
      if (treeCheckbox) {
        treeCheckbox.checked = shouldSelect;
      }

      updateOrgTreeSelectedInputs();
      triggerOrgFilterUpdate();

      // Clear sidebar search results
      const searchResults = document.getElementById("org-tree-search-results");
      if (searchResults) {
        searchResults.innerHTML = "";
      }
    }
  };

  // Helper function for modal parent state updates (needs to be accessible)
  function updateModalParentCheckboxStates(startNode) {
    if (!startNode) return;

    let currentNode = startNode.parentElement?.closest(".org-tree-node");

    while (currentNode) {
      const parentCheckbox = currentNode.querySelector(
        ":scope > .org-tree-node__header .org-tree-node__checkbox",
      );
      const childrenContainer = currentNode.querySelector(
        ":scope > .org-tree-node__children",
      );

      if (parentCheckbox && childrenContainer) {
        const childCheckboxes = childrenContainer.querySelectorAll(
          ".org-tree-node__checkbox",
        );

        if (childCheckboxes.length > 0) {
          const checkedCount = Array.from(childCheckboxes).filter(
            (cb) => cb.checked,
          ).length;
          const indeterminateCount = Array.from(childCheckboxes).filter(
            (cb) => cb.indeterminate,
          ).length;

          if (checkedCount === 0 && indeterminateCount === 0) {
            parentCheckbox.checked = false;
            parentCheckbox.indeterminate = false;
          } else if (
            checkedCount === childCheckboxes.length &&
            indeterminateCount === 0
          ) {
            parentCheckbox.checked = true;
            parentCheckbox.indeterminate = false;
          } else {
            parentCheckbox.checked = false;
            parentCheckbox.indeterminate = true;
          }
        }
      }

      currentNode = currentNode.parentElement?.closest(".org-tree-node");
    }
  }

  function updateOrgTreeSelectedInputs() {
    const container = document.getElementById("org-tree-selected-inputs");
    if (!container) return;

    // Collect all checked checkboxes in the tree
    const checkedBoxes = document.querySelectorAll(
      ".org-tree-filter .org-tree-node__checkbox:checked",
    );
    const selectedIds = new Set();
    checkedBoxes.forEach((cb) => selectedIds.add(cb.value));

    // Also check search result checkboxes
    const searchCheckedBoxes = document.querySelectorAll(
      ".org-tree-search-result input[type='checkbox']:checked",
    );
    searchCheckedBoxes.forEach((cb) =>
      selectedIds.add(
        cb.value || cb.closest(".org-tree-search-result").dataset?.orgId,
      ),
    );

    // Update hidden inputs
    container.innerHTML = "";
    selectedIds.forEach((id) => {
      if (id) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "org_id";
        input.value = id;
        input.setAttribute("data-filter-input", "");
        container.appendChild(input);
      }
    });
  }

  function triggerOrgFilterUpdate() {
    const form = document.querySelector(".filter-sidebar-form");
    if (form) {
      htmx.trigger(form, "change");
    }
  }

  // ============================================================================
  // DATE RANGE VALIDATION AND SETUP
  // ============================================================================

  function setupDateRangeListeners() {
    const form = document.querySelector(".filter-sidebar-form");
    if (!form) return;

    const dateRangeInputs = document.querySelectorAll('input[type="date"]');

    dateRangeInputs.forEach((input) => {
      input.addEventListener("change", function (event) {
        event.stopPropagation(); // Prevent htmx from triggering on individual date changes

        const requireBoth = input.dataset.requireBoth === "true";
        const combinedName = input.dataset.combinedName;
        const pairId = input.dataset.pairId;

        if (requireBoth && combinedName && pairId) {
          const pairInput = document.getElementById(pairId);
          const validationMessage = document.getElementById(
            `${combinedName}-validation-message`,
          );
          const hiddenOutput = form.querySelector(
            `input[name="${combinedName}"]`,
          );

          if (!pairInput || !hiddenOutput) return;

          const fromInput = input.id.includes("-from") ? input : pairInput;
          const toInput = input.id.includes("-to") ? input : pairInput;

          const fromValue = fromInput.value;
          const toValue = toInput.value;

          // Show/hide validation message
          if (validationMessage) {
            if ((fromValue && !toValue) || (!fromValue && toValue)) {
              validationMessage.style.display = "block";
            } else {
              validationMessage.style.display = "none";
            }
          }

          // Update hidden output field
          if (fromValue && toValue) {
            // Both dates provided - set combined value
            hiddenOutput.value = `${fromValue}_${toValue}`;
            // Trigger htmx now that we have a valid range
            htmx.trigger(form, "change");
          } else {
            // Clear value (but keep name attribute)
            hiddenOutput.value = "";
          }
        }
      });
    });
  }

  // ============================================================================
  // INITIALIZATION AND HTMX INTEGRATION
  // ============================================================================

  // Setup date range listeners on initial load
  setupDateRangeListeners();

  // Initialize org tree checkbox states on page load
  initializeOrgTreeCheckboxStates();

  // Auto-expand to selected nodes
  autoExpandOrgTreeNodes();

  // Listen for HTMX afterSwap event to re-initialize after content swap
  document.body.addEventListener("htmx:afterSwap", function (event) {
    // Only restore if the swap target was the filter container
    if (event.detail.target.id === "filter-and-table-container") {
      setupDateRangeListeners(); // Re-attach date range listeners to new elements
      initializeOrgTreeCheckboxStates(); // Re-initialize org tree states
    }

    // After loading tree children, update parent states
    if (event.detail.target.id?.startsWith("org-tree-children-")) {
      const parentNode = event.detail.target.closest(".org-tree-node");
      if (parentNode) {
        // Check if parent was checked - if so, check all new children
        const parentCheckbox = parentNode.querySelector(
          ":scope > .org-tree-node__header .org-tree-node__checkbox",
        );
        if (parentCheckbox?.checked) {
          const childCheckboxes = event.detail.target.querySelectorAll(
            ".org-tree-node__checkbox",
          );
          childCheckboxes.forEach((cb) => {
            cb.checked = true;
          });
          updateOrgTreeSelectedInputs();
        }
        // Update tri-state based on loaded children
        updateParentCheckboxStates(event.detail.target);
      }
    }
  });

  // Keyboard navigation for org tree
  document.addEventListener("keydown", function (event) {
    const activeElement = document.activeElement;
    // Check if we're in a tree (sidebar or modal)
    const treeContainer = activeElement?.closest(
      ".org-tree-filter__tree, .org-filter-modal__tree, #org-modal-tree-view",
    );
    if (!treeContainer) return;

    const currentNode = activeElement.closest(".org-tree-node");
    if (!currentNode) return;

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        focusNextNode(currentNode);
        break;
      case "ArrowUp":
        event.preventDefault();
        focusPreviousNode(currentNode);
        break;
      case "ArrowRight":
        event.preventDefault();
        expandNode(currentNode);
        break;
      case "ArrowLeft":
        event.preventDefault();
        collapseOrFocusParent(currentNode);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        toggleNodeCheckbox(currentNode);
        break;
    }
  });

  function focusNextNode(currentNode) {
    // If expanded, go to first child
    if (currentNode.getAttribute("aria-expanded") === "true") {
      const firstChild = currentNode.querySelector(
        ".org-tree-node__children > .org-tree-node",
      );
      if (firstChild) {
        focusNode(firstChild);
        return;
      }
    }

    // Otherwise, go to next sibling or parent's next sibling
    let node = currentNode;
    while (node) {
      const nextSibling = node.nextElementSibling;
      if (nextSibling?.classList.contains("org-tree-node")) {
        focusNode(nextSibling);
        return;
      }
      // Move up to parent
      node = node.parentElement?.closest(".org-tree-node");
    }
  }

  function focusPreviousNode(currentNode) {
    const prevSibling = currentNode.previousElementSibling;
    if (prevSibling?.classList.contains("org-tree-node")) {
      // Go to the last visible descendant of previous sibling
      let target = prevSibling;
      while (target.getAttribute("aria-expanded") === "true") {
        const children = target.querySelectorAll(
          ":scope > .org-tree-node__children > .org-tree-node",
        );
        if (children.length > 0) {
          target = children[children.length - 1];
        } else {
          break;
        }
      }
      focusNode(target);
      return;
    }

    // Go to parent
    const parent = currentNode.parentElement?.closest(".org-tree-node");
    if (parent) {
      focusNode(parent);
    }
  }

  function expandNode(node) {
    if (node.getAttribute("aria-expanded") === "false") {
      const toggle = node.querySelector(".org-tree-node__toggle");
      if (toggle) {
        toggle.click();
      }
    } else {
      // If already expanded, move to first child
      const firstChild = node.querySelector(
        ".org-tree-node__children > .org-tree-node",
      );
      if (firstChild) {
        focusNode(firstChild);
      }
    }
  }

  function collapseOrFocusParent(node) {
    if (node.getAttribute("aria-expanded") === "true") {
      // Collapse
      node.setAttribute("aria-expanded", "false");
      const toggle = node.querySelector(".org-tree-node__toggle");
      if (toggle) {
        toggle.classList.remove("org-tree-node__toggle--expanded");
      }
    } else {
      // Focus parent
      const parent = node.parentElement?.closest(".org-tree-node");
      if (parent) {
        focusNode(parent);
      }
    }
  }

  function toggleNodeCheckbox(node) {
    const checkbox = node.querySelector(
      ":scope > .org-tree-node__header .org-tree-node__checkbox",
    );
    if (checkbox) {
      checkbox.checked = !checkbox.checked;
      handleOrgTreeCheckboxChange(checkbox);
    }
  }

  function focusNode(node) {
    const checkbox = node.querySelector(
      ":scope > .org-tree-node__header .org-tree-node__checkbox",
    );
    if (checkbox) {
      checkbox.focus();
    }
  }

  // Initialize tri-state for org tree checkboxes based on selected IDs
  function initializeOrgTreeCheckboxStates() {
    const treeContainer = document.querySelector(".org-tree-filter__tree");
    if (!treeContainer) return;

    // Get all root-level nodes and update their states
    const rootNodes = treeContainer.querySelectorAll(":scope > .org-tree-node");
    rootNodes.forEach((node) => {
      updateNodeTriState(node);
    });
  }

  // Auto-expand nodes to show selected organizations
  function autoExpandOrgTreeNodes() {
    const treeFilter = document.getElementById("org-tree-filter");
    if (!treeFilter) return;

    const expandIdsStr = treeFilter.dataset.expandIds;
    if (!expandIdsStr) return;

    const expandIds = expandIdsStr.split(",").filter((id) => id);
    if (expandIds.length === 0) return;

    // Expand nodes in order (parents first)
    expandIds.forEach((orgId) => {
      const node = document.querySelector(
        `.org-tree-node[data-org-id="${orgId}"]`,
      );
      if (node && node.getAttribute("aria-expanded") === "false") {
        const toggle = node.querySelector(".org-tree-node__toggle");
        if (toggle) {
          // Trigger the HTMX request to load children
          toggle.click();
        }
      }
    });
  }

  // Auto-expand modal tree nodes to show selected organizations
  // Uses a queue to expand nodes sequentially, waiting for each to load
  let modalExpandQueue = [];

  function autoExpandModalTreeNodes() {
    const treeView = document.getElementById("org-modal-tree-view");
    if (!treeView) return;

    const expandIdsStr = treeView.dataset.expandIds;
    if (!expandIdsStr) return;

    const expandIds = expandIdsStr.split(",").filter((id) => id);
    if (expandIds.length === 0) return;

    // Store the expand queue and start expanding
    modalExpandQueue = [...expandIds];
    expandNextModalNode();
  }

  function expandNextModalNode() {
    if (modalExpandQueue.length === 0) return;

    const orgId = modalExpandQueue.shift();
    const treeView = document.getElementById("org-modal-tree-view");
    if (!treeView) return;

    const node = treeView.querySelector(
      `.org-tree-node[data-org-id="${orgId}"]`,
    );
    if (node && node.getAttribute("aria-expanded") === "false") {
      const toggle = node.querySelector("button.org-tree-node__toggle");
      if (toggle) {
        // Click the toggle to expand and load children
        toggle.click();
        // The htmx:afterSwap handler will call expandNextModalNode when children are loaded
      } else {
        // No toggle button, try next node
        expandNextModalNode();
      }
    } else {
      // Node already expanded or doesn't exist yet, try next
      expandNextModalNode();
    }
  }

  // Listen for modal tree children being loaded to continue auto-expand
  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (
      event.detail.target.id &&
      event.detail.target.id.startsWith("org-tree-children-modal-")
    ) {
      // Children loaded, continue expanding the queue
      if (modalExpandQueue.length > 0) {
        // Small delay to let the DOM update
        setTimeout(expandNextModalNode, 50);
      }
    }
  });

  // Recursively update tri-state for a node based on its children
  function updateNodeTriState(node) {
    const checkbox = node.querySelector(
      ":scope > .org-tree-node__header .org-tree-node__checkbox",
    );
    const childrenContainer = node.querySelector(
      ":scope > .org-tree-node__children",
    );

    if (!checkbox) return;

    // If children are loaded, check their state
    if (childrenContainer && childrenContainer.children.length > 0) {
      const childNodes = childrenContainer.querySelectorAll(
        ":scope > .org-tree-node",
      );

      // First, recursively update children
      childNodes.forEach((childNode) => updateNodeTriState(childNode));

      // Then update this node based on children
      const childCheckboxes = childrenContainer.querySelectorAll(
        ".org-tree-node__checkbox",
      );

      if (childCheckboxes.length > 0) {
        const checkedCount = Array.from(childCheckboxes).filter(
          (cb) => cb.checked,
        ).length;
        const indeterminateCount = Array.from(childCheckboxes).filter(
          (cb) => cb.indeterminate,
        ).length;

        if (checkedCount === 0 && indeterminateCount === 0) {
          checkbox.indeterminate = false;
        } else if (
          checkedCount === childCheckboxes.length &&
          indeterminateCount === 0
        ) {
          checkbox.indeterminate = false;
        } else {
          checkbox.indeterminate = true;
        }
      }
    }
  }

  // Handle back button navigation - reload page to sync filters with URL
  window.addEventListener("popstate", function (event) {
    window.location.href = window.location.href;
  });

  // ============================================================================
  // ORGANIZATION FILTER MODAL
  // ============================================================================

  // Expand tree node in modal - handles HTMX request with selected IDs
  window.expandOrgTreeNodeModal = function (button, nodeId) {
    const treeNode = button.closest(".org-tree-node");
    if (!treeNode) return;

    const isExpanded = treeNode.getAttribute("aria-expanded") === "true";

    if (isExpanded) {
      // Collapse - just toggle visual state
      treeNode.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-expanded", "false");
      button.classList.remove("org-tree-node__toggle--expanded");
    } else {
      // Expand - toggle visual state and load children
      treeNode.setAttribute("aria-expanded", "true");
      button.setAttribute("aria-expanded", "true");
      button.classList.add("org-tree-node__toggle--expanded");

      // Check if children already loaded
      const childrenContainer = document.getElementById(
        `org-tree-children-modal-${nodeId}`,
      );
      if (childrenContainer && childrenContainer.children.length === 0) {
        // Build URL with selected org_ids
        const params = new URLSearchParams();
        const modalInputs = document.getElementById(
          "org-modal-selected-inputs",
        );
        if (modalInputs) {
          modalInputs
            .querySelectorAll('input[name="org_id"]')
            .forEach((input) => {
              if (input.value) {
                params.append("org_id", input.value);
              }
            });
        }

        const baseUrl = `/plaatsingen/opdrachtgever/tree-modal/${nodeId}/`;
        const url = params.toString()
          ? `${baseUrl}?${params.toString()}`
          : baseUrl;

        // Make HTMX request
        htmx.ajax("GET", url, {
          target: `#org-tree-children-modal-${nodeId}`,
          swap: "innerHTML",
        });
      }
    }
  };

  // Toggle expand/collapse for tree node
  window.toggleOrgTreeNode = function (button) {
    const treeNode = button.closest(".org-tree-node");
    if (!treeNode) return;

    const isExpanded = treeNode.getAttribute("aria-expanded") === "true";

    if (isExpanded) {
      // Collapse
      treeNode.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-expanded", "false");
      button.classList.remove("org-tree-node__toggle--expanded");
    } else {
      // Expand
      treeNode.setAttribute("aria-expanded", "true");
      button.setAttribute("aria-expanded", "true");
      button.classList.add("org-tree-node__toggle--expanded");
    }
  };

  // Handle checkbox change in modal
  window.handleOrgModalCheckboxChange = function (checkbox) {
    // Clear indeterminate state when explicitly clicked
    checkbox.indeterminate = false;

    const isChecked = checkbox.checked;
    const treeNode = checkbox.closest(".org-tree-node");

    // Cascade to all visible children - when parent is checked/unchecked,
    // all children should reflect the same state for visual consistency
    const childCheckboxes = treeNode.querySelectorAll(
      ".org-tree-node__checkbox",
    );
    childCheckboxes.forEach((cb) => {
      cb.checked = isChecked;
      cb.indeterminate = false;
    });

    // Update parent checkbox states (tri-state)
    updateModalParentCheckboxStates(treeNode);

    // Update selected panel and hidden inputs
    updateOrgModalSelection();
  };

  // Update selected panel and hidden inputs in modal
  function updateOrgModalSelection() {
    const modal = document.getElementById("org-filter-modal");
    if (!modal) return;

    // Collect all checked checkboxes
    const checkedBoxes = modal.querySelectorAll(
      ".org-tree-node__checkbox:checked",
    );
    const selectedOrgs = new Map();
    checkedBoxes.forEach((cb) => {
      selectedOrgs.set(cb.value, cb.dataset.orgName || cb.value);
    });

    // Update hidden inputs
    const inputsContainer = document.getElementById(
      "org-modal-selected-inputs",
    );
    if (inputsContainer) {
      inputsContainer.innerHTML = "";
      selectedOrgs.forEach((name, id) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "org_id";
        input.value = id;
        inputsContainer.appendChild(input);
      });
    }

    // Update selected list
    const selectedList = document.getElementById("org-modal-selected-list");
    if (selectedList) {
      if (selectedOrgs.size === 0) {
        selectedList.innerHTML =
          '<li class="org-filter-modal__selected-empty">Geen opdrachtgevers geselecteerd</li>';
      } else {
        selectedList.innerHTML = "";
        selectedOrgs.forEach((name, id) => {
          const li = document.createElement("li");
          li.className = "org-filter-modal__selected-item";
          li.dataset.orgId = id;
          li.innerHTML = `
            <span class="org-filter-modal__selected-name">${name}</span>
            <button type="button"
                    class="org-filter-modal__selected-remove"
                    onclick="removeOrgFromModalSelection(${id})"
                    aria-label="Verwijder ${name}">
              <c-icon icon="kruis" color="grijs-600" size="sm"></c-icon>
            </button>
          `;
          selectedList.appendChild(li);
        });
      }
    }

    // Update count badge
    const countBadge = document.getElementById("org-modal-selected-count");
    if (countBadge) {
      countBadge.textContent = selectedOrgs.size;
    }

    // Show/hide clear button based on selection
    const clearBtn = document.getElementById("org-modal-clear-btn");
    if (clearBtn) {
      clearBtn.hidden = selectedOrgs.size === 0;
    }
  }

  // Open the organization filter modal with current selection
  window.openOrgFilterModal = function () {
    // Get selected org_ids from URL (source of truth) instead of hidden inputs
    const currentUrl = new URL(window.location.href);
    const orgIds = currentUrl.searchParams.getAll("org_id");

    const params = new URLSearchParams();
    orgIds.forEach((id) => {
      if (id) {
        params.append("org_id", id);
      }
    });

    // Build URL with parameters
    const baseUrl = "/plaatsingen/opdrachtgever/filter/";
    const url = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;

    // Make HTMX request
    htmx.ajax("GET", url, {
      target: "#org-filter-modal-container",
      swap: "innerHTML",
    });
  };

  // Remove organization from modal selection
  window.removeOrgFromModalSelection = function (orgId) {
    const modal = document.getElementById("org-filter-modal");
    if (!modal) return;

    // Uncheck the checkbox in the tree
    const checkbox = modal.querySelector(
      `.org-tree-node__checkbox[value="${orgId}"]`,
    );
    if (checkbox) {
      checkbox.checked = false;
      checkbox.indeterminate = false;
      const treeNode = checkbox.closest(".org-tree-node");
      updateModalParentCheckboxStates(treeNode);
    }

    // Update selection panel
    updateOrgModalSelection();
  };

  // Clear all selections in modal
  window.clearAllOrgModalSelections = function () {
    const modal = document.getElementById("org-filter-modal");
    if (!modal) return;

    const checkboxes = modal.querySelectorAll(".org-tree-node__checkbox");
    checkboxes.forEach((cb) => {
      cb.checked = false;
      cb.indeterminate = false;
    });

    updateOrgModalSelection();
  };

  // Apply modal filter and close
  window.applyOrgModalFilter = function () {
    const modal = document.getElementById("org-filter-modal");
    if (!modal) return;

    // Collect selected IDs
    const inputsContainer = document.getElementById(
      "org-modal-selected-inputs",
    );
    const selectedIds = [];
    if (inputsContainer) {
      inputsContainer.querySelectorAll("input").forEach((input) => {
        selectedIds.push(input.value);
      });
    }

    // Update the sidebar's hidden inputs
    const sidebarInputs = document.getElementById("org-tree-selected-inputs");
    if (sidebarInputs) {
      sidebarInputs.innerHTML = "";
      selectedIds.forEach((id) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "org_id";
        input.value = id;
        input.setAttribute("data-filter-input", "");
        sidebarInputs.appendChild(input);
      });
    }

    // Close modal
    modal.close();

    // Trigger filter update
    const form = document.querySelector(".filter-sidebar-form");
    if (form) {
      htmx.trigger(form, "change");
    }
  };

  // Handle modal opening - initialize HTMX for the dialog
  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target.id === "org-filter-modal-container") {
      const dialog = event.detail.target.querySelector("dialog");
      if (dialog) {
        dialog.showModal();

        // Auto-expand to show selected organizations
        autoExpandModalTreeNodes();

        // Add close button handlers - only for explicit close buttons
        const closeButton = dialog.querySelector(".modal-close-button");
        if (closeButton) {
          closeButton.addEventListener("click", (e) => {
            e.stopPropagation();
            dialog.close();
          });
        }

        // Annuleren button
        const cancelBtn = dialog.querySelector(".modal-footer .close");
        if (cancelBtn) {
          cancelBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            dialog.close();
          });
        }

        // Clear filter button - clears selections and immediately applies (closes modal)
        const clearBtn = dialog.querySelector("#org-modal-clear-btn");
        if (clearBtn) {
          clearBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            clearAllOrgModalSelections();
            applyOrgModalFilter();
          });
        }

        // Apply filter button
        const applyBtn = dialog.querySelector("#org-modal-apply-btn");
        if (applyBtn) {
          applyBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            applyOrgModalFilter();
          });
        }

        // Search input - toggle between tree and search results
        const searchInput = dialog.querySelector("#org-modal-search-input");
        if (searchInput) {
          searchInput.addEventListener("input", (e) => {
            const query = e.target.value.trim();
            const treeView = document.getElementById("org-modal-tree-view");
            const searchResults = document.getElementById(
              "org-modal-search-results",
            );

            if (query.length >= 2) {
              // Show search results, hide tree
              if (treeView) treeView.hidden = true;
              if (searchResults) searchResults.hidden = false;
            } else {
              // Show tree, hide search results
              if (treeView) treeView.hidden = false;
              if (searchResults) {
                searchResults.hidden = true;
                searchResults.innerHTML = "";
              }
            }
          });
        }

        // Close on backdrop click only - check if click is on dialog backdrop
        dialog.addEventListener("click", (e) => {
          // Only close if clicking directly on the dialog element (backdrop)
          // Not on any child elements
          const rect = dialog.getBoundingClientRect();
          const isInDialog =
            e.clientX >= rect.left &&
            e.clientX <= rect.right &&
            e.clientY >= rect.top &&
            e.clientY <= rect.bottom;

          // If click is outside the visible dialog content, it's on backdrop
          const content = dialog.querySelector(".modal-content");
          if (content) {
            const contentRect = content.getBoundingClientRect();
            const isInContent =
              e.clientX >= contentRect.left &&
              e.clientX <= contentRect.right &&
              e.clientY >= contentRect.top &&
              e.clientY <= contentRect.bottom;

            if (isInDialog && !isInContent) {
              dialog.close();
            }
          }
        });
      }
    }

    // Handle modal tree children loading - update parent checkbox states
    // Note: Don't call updateOrgModalSelection() here as it would overwrite
    // the server-rendered hidden inputs. The children are already rendered
    // with correct checked state from the server based on selected_ids.
    if (event.detail.target.id?.startsWith("org-tree-children-modal-")) {
      const parentNode = event.detail.target.closest(".org-tree-node");
      if (parentNode) {
        updateModalParentCheckboxStates(event.detail.target);
      }
    }
  });
});
