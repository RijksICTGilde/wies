// Checkbox filter component — top-N inline checkboxes + a "Meer" modal.
// Uses event delegation so listeners survive OOB swaps.
(function () {
  // Track which filter groups are manually collapsed (survives OOB swaps)
  var collapsedGroups = new Set();

  function getGroupKey(container) {
    return container.dataset.groupId || container.dataset.name;
  }

  // Rebuild a sidebar group's hidden inputs from its checked inline checkboxes.
  function syncHiddenInputs(container) {
    var name = container.dataset.name;
    var hiddenContainer = container.querySelector(
      ".checkbox-filter__hidden-inputs",
    );
    if (!hiddenContainer) return;

    hiddenContainer.innerHTML = "";
    var checked = container.querySelectorAll(
      ".checkbox-filter__checkbox:checked",
    );
    checked.forEach(function (cb) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = cb.value;
      input.setAttribute("data-filter-input", "");
      hiddenContainer.appendChild(input);
    });
  }

  // Find the sidebar group fieldset for a given group_id.
  function findSidebarGroup(groupId) {
    return document.querySelector(
      '[data-checkbox-filter][data-group-id="' + groupId + '"]',
    );
  }

  // Set a single value's hidden input + inline checkbox state for a group,
  // without disturbing the group's other selections. Used by the modal, whose
  // option may not exist among the inline top-N checkboxes.
  function setGroupValue(container, value, checked) {
    var name = container.dataset.name;
    var hiddenContainer = container.querySelector(
      ".checkbox-filter__hidden-inputs",
    );
    if (!hiddenContainer) return;

    // Reflect onto the inline checkbox if it's shown.
    var inline = container.querySelector(
      '.checkbox-filter__checkbox[value="' + value + '"]',
    );
    if (inline) inline.checked = checked;

    var existing = hiddenContainer.querySelector(
      'input[value="' + value + '"]',
    );
    if (checked && !existing) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      input.setAttribute("data-filter-input", "");
      hiddenContainer.appendChild(input);
    } else if (!checked && existing) {
      existing.remove();
    }
  }

  function triggerSidebarForm() {
    var form = document.querySelector(".filter-sidebar-form");
    if (form && typeof htmx !== "undefined") htmx.trigger(form, "change");
  }

  // Restore collapsed state after OOB swap
  function restoreState() {
    document
      .querySelectorAll("[data-checkbox-filter]")
      .forEach(function (container) {
        if (collapsedGroups.has(getGroupKey(container))) {
          var body = container.querySelector(".checkbox-filter__body");
          var header = container.querySelector(".checkbox-filter__header");
          if (body) body.hidden = true;
          if (header)
            header.classList.add("checkbox-filter__header--collapsed");
        }
      });
  }

  // --------------------------------------------------------------------------
  // Inline checkbox change — capture phase to stopPropagation before the
  // form's hx-trigger fires, then submit once with the synced inputs.
  // --------------------------------------------------------------------------
  document.addEventListener(
    "change",
    function (e) {
      if (!e.target.matches(".checkbox-filter__checkbox")) return;
      e.stopPropagation();
      var container = e.target.closest("[data-checkbox-filter]");
      if (!container) return;
      syncHiddenInputs(container);
      triggerSidebarForm();
    },
    true,
  ); // capture phase

  // --------------------------------------------------------------------------
  // Modal checkbox change — update the matching sidebar group and submit.
  // --------------------------------------------------------------------------
  document.addEventListener(
    "change",
    function (e) {
      if (!e.target.matches(".filter-options-modal__checkbox")) return;
      e.stopPropagation();
      var modal = e.target.closest("#filterOptionsModal");
      if (!modal) return;
      var container = findSidebarGroup(modal.dataset.groupId);
      if (!container) return;
      setGroupValue(container, e.target.value, e.target.checked);
      triggerSidebarForm();
    },
    true,
  ); // capture phase

  // Section collapse via header chevron
  document.addEventListener("click", function (e) {
    var headerBtn = e.target.closest(".checkbox-filter__header");
    if (!headerBtn) return;
    e.preventDefault();
    var container = headerBtn.closest("[data-checkbox-filter]");
    if (!container) return;
    var body = container.querySelector(".checkbox-filter__body");
    if (!body) return;
    var isCollapsed = body.hidden;
    body.hidden = !isCollapsed;
    headerBtn.classList.toggle(
      "checkbox-filter__header--collapsed",
      !isCollapsed,
    );
    var key = getGroupKey(container);
    if (isCollapsed) collapsedGroups.delete(key);
    else collapsedGroups.add(key);
  });

  // --------------------------------------------------------------------------
  // Modal search: filter the alphabetical option list by typed text.
  // --------------------------------------------------------------------------
  function filterModalOptions(modal, query) {
    var q = query.trim().toLowerCase();
    modal
      .querySelectorAll(".filter-options-modal__option")
      .forEach(function (opt) {
        var label = opt.dataset.optionLabel || "";
        opt.hidden = q !== "" && label.indexOf(q) === -1;
      });
  }

  document.addEventListener("input", function (e) {
    if (e.target.id !== "filter-options-search") return;
    var modal = e.target.closest("#filterOptionsModal");
    if (modal) filterModalOptions(modal, e.target.value);
  });

  // Clear modal search via its × button
  document.addEventListener("click", function (e) {
    if (!e.target.closest("#filterOptionsModal .search-clear")) return;
    var modal = e.target.closest("#filterOptionsModal");
    if (modal) filterModalOptions(modal, "");
  });

  // Focus the search field when the modal opens
  document.addEventListener("htmx:afterSettle", function (e) {
    if (
      e.detail.target &&
      e.detail.target.id === "filterOptionsModalContainer"
    ) {
      var search = document.getElementById("filter-options-search");
      if (search) search.focus();
    }
  });

  // Public API: uncheck a single value (used by chip removal)
  // Searches ALL containers with matching name (multiple categories share data-name="labels")
  window.checkboxFilterUncheck = function (name, value) {
    document
      .querySelectorAll('[data-checkbox-filter][data-name="' + name + '"]')
      .forEach(function (container) {
        setGroupValue(container, value, false);
      });
  };

  // Public API: clear all checkbox filters within a scope
  window.checkboxFilterClearAll = function (scope) {
    (scope || document)
      .querySelectorAll("[data-checkbox-filter]")
      .forEach(function (container) {
        container
          .querySelectorAll(".checkbox-filter__checkbox")
          .forEach(function (cb) {
            cb.checked = false;
          });
        var hidden = container.querySelector(".checkbox-filter__hidden-inputs");
        if (hidden) hidden.innerHTML = "";
      });
  };

  // Restore collapsed state after OOB swap
  document.addEventListener("htmx:afterSettle", restoreState);
})();
