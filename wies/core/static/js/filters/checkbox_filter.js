// Checkbox filter component — NDD Design System (ndd-checkbox-field)
// ndd-checkbox-field dispatches change with bubbles:true but NOT composed:true,
// so the event does not cross Shadow DOM boundaries. We attach listeners directly.
(function () {
  // Track which filter groups are manually expanded/collapsed (survives OOB swaps)
  var expandedGroups = new Set();
  var collapsedGroups = new Set();

  function getGroupKey(container) {
    var legend = container.querySelector(".checkbox-filter__label");
    return (
      container.dataset.name + ":" + (legend ? legend.textContent.trim() : "")
    );
  }

  function syncHiddenInputs(container) {
    var name = container.dataset.name;
    var hiddenContainer = container.querySelector(
      ".checkbox-filter__hidden-inputs",
    );
    if (!hiddenContainer) return;

    hiddenContainer.innerHTML = "";
    var checkboxes = container.querySelectorAll(
      "ndd-checkbox-field.checkbox-filter__checkbox",
    );
    checkboxes.forEach(function (cb) {
      if (cb.checked) {
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = cb.value;
        input.setAttribute("data-filter-input", "");
        hiddenContainer.appendChild(input);
      }
    });
  }

  function onCheckboxChange(e) {
    var cb = e.currentTarget;
    var container = cb.closest("[data-checkbox-filter]");
    if (!container) return;
    syncHiddenInputs(container);
    // Trigger HTMX by dispatching change on a hidden input with data-filter-input
    var form = container.closest("form");
    if (form) {
      var anyInput = form.querySelector("[data-filter-input]");
      if (anyInput) {
        anyInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
  }

  function attachCheckboxListeners() {
    document
      .querySelectorAll("ndd-checkbox-field.checkbox-filter__checkbox")
      .forEach(function (cb) {
        // Avoid double-attaching
        if (cb._filterListenerAttached) return;
        cb._filterListenerAttached = true;
        cb.addEventListener("change", onCheckboxChange);
      });
  }

  // Restore expanded/collapsed state after OOB swap
  function restoreState() {
    document
      .querySelectorAll("[data-checkbox-filter]")
      .forEach(function (container) {
        var key = getGroupKey(container);

        if (expandedGroups.has(key)) {
          var extra = container.querySelector(
            ".checkbox-filter__options--extra",
          );
          var toggle = container.querySelector(".checkbox-filter__toggle");
          if (
            extra &&
            extra.classList.contains("checkbox-filter__options--hidden")
          ) {
            extra.classList.remove("checkbox-filter__options--hidden");
            if (toggle) {
              toggle.classList.add("checkbox-filter__toggle--expanded");
              toggle.setAttribute("text", "Toon minder");
              toggle.setAttribute("start-icon", "minus");
            }
          }
        }

        if (collapsedGroups.has(key)) {
          var body = container.querySelector(".checkbox-filter__body");
          if (body) body.classList.add("checkbox-filter__body--hidden");
        }
      });
    attachCheckboxListeners();
  }

  // Toggle section collapse via header chevron
  document.addEventListener("click", function (e) {
    // ndd-button uses Shadow DOM — find the host element via composedPath
    var path = e.composedPath();
    var hostEl = path.find(function (el) {
      return (
        el.classList &&
        (el.classList.contains("checkbox-filter__header") ||
          el.classList.contains("checkbox-filter__toggle"))
      );
    });
    var headerBtn =
      hostEl && hostEl.classList.contains("checkbox-filter__header")
        ? hostEl
        : null;
    var toggleBtn =
      hostEl && hostEl.classList.contains("checkbox-filter__toggle")
        ? hostEl
        : null;

    if (!headerBtn)
      headerBtn =
        e.target.closest && e.target.closest(".checkbox-filter__header");
    if (headerBtn) {
      e.preventDefault();
      var container = headerBtn.closest("[data-checkbox-filter]");
      if (!container) return;
      var body = container.querySelector(".checkbox-filter__body");
      if (!body) return;
      var isCollapsed = body.classList.contains(
        "checkbox-filter__body--hidden",
      );
      body.classList.toggle("checkbox-filter__body--hidden", !isCollapsed);

      var key = getGroupKey(container);
      if (isCollapsed) {
        collapsedGroups.delete(key);
      } else {
        collapsedGroups.add(key);
      }
      return;
    }

    // Toggle "Toon meer"/"Toon minder"
    if (!toggleBtn)
      toggleBtn =
        e.target.closest && e.target.closest(".checkbox-filter__toggle");
    if (!toggleBtn) return;
    e.preventDefault();
    var container = toggleBtn.closest("[data-checkbox-filter]");
    if (!container) return;
    var extraOptions = container.querySelector(
      ".checkbox-filter__options--extra",
    );
    if (!extraOptions) return;
    var isExpanded = !extraOptions.classList.contains(
      "checkbox-filter__options--hidden",
    );
    extraOptions.classList.toggle(
      "checkbox-filter__options--hidden",
      isExpanded,
    );
    // Update ndd-button attributes for text and icon
    toggleBtn.setAttribute("text", isExpanded ? "Toon meer" : "Toon minder");
    toggleBtn.setAttribute("start-icon", isExpanded ? "add" : "minus");
    toggleBtn.classList.toggle(
      "checkbox-filter__toggle--expanded",
      !isExpanded,
    );

    var key = getGroupKey(container);
    if (isExpanded) {
      expandedGroups.delete(key);
    } else {
      expandedGroups.add(key);
    }
  });

  // Public API: uncheck a single value (used by chip removal)
  window.checkboxFilterUncheck = function (name, value) {
    document
      .querySelectorAll('[data-checkbox-filter][data-name="' + name + '"]')
      .forEach(function (container) {
        var cb = container.querySelector(
          'ndd-checkbox-field.checkbox-filter__checkbox[value="' + value + '"]',
        );
        if (cb) {
          cb.checked = false;
          syncHiddenInputs(container);
        }
      });
  };

  // Public API: clear all checkbox filters within a scope
  window.checkboxFilterClearAll = function (scope) {
    (scope || document)
      .querySelectorAll("[data-checkbox-filter]")
      .forEach(function (container) {
        container
          .querySelectorAll("ndd-checkbox-field.checkbox-filter__checkbox")
          .forEach(function (cb) {
            cb.checked = false;
          });
        syncHiddenInputs(container);
      });
  };

  // Handle ndd-token dismiss — removes filter and re-triggers HTMX
  // ndd-token dispatches "dismiss" with bubbles:true, composed:true
  document.addEventListener("dismiss", function (e) {
    var path = e.composedPath();
    var token = path.find(function (el) {
      return (
        el instanceof Element &&
        el.tagName &&
        el.tagName.toLowerCase() === "ndd-token"
      );
    });
    if (!token) return;

    var filterType = token.dataset.filterType;
    var filterName = token.dataset.filterName;
    var filterValue = token.dataset.filterValue;

    if (filterType === "select-multi") {
      if (typeof window.checkboxFilterUncheck === "function") {
        window.checkboxFilterUncheck(filterName, filterValue);
      }
      // Trigger HTMX via hidden input change
      var anyInput = document.querySelector("[data-filter-input]");
      if (anyInput) {
        anyInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } else if (filterType === "zoek") {
      var hiddenSearch = document.getElementById("search-filter-value");
      if (hiddenSearch) {
        hiddenSearch.value = "";
        hiddenSearch.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } else if (filterType === "date") {
      // ndd-text-field: set value attribute to empty
      var dateField = document.getElementById("filter-" + filterName);
      if (dateField) {
        dateField.value = "";
        // Also clear the hidden input if any
        var hiddenDate = document.querySelector(
          'input[name="' + filterName + '"][data-filter-input]',
        );
        if (hiddenDate) {
          hiddenDate.value = "";
          hiddenDate.dispatchEvent(new Event("change", { bubbles: true }));
        } else {
          var anyInput2 = document.querySelector("[data-filter-input]");
          if (anyInput2)
            anyInput2.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
    } else if (filterType === "org") {
      var orgContainer = document.getElementById("org-filter-inputs");
      if (orgContainer) {
        orgContainer
          .querySelectorAll('input[name="' + filterName + '"]')
          .forEach(function (inp) {
            if (inp.value === filterValue) inp.remove();
          });
      }
      var anyInput3 = document.querySelector("[data-filter-input]");
      if (anyInput3)
        anyInput3.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  // Initial attach + restore state after OOB swap
  document.addEventListener("DOMContentLoaded", attachCheckboxListeners);
  document.addEventListener("htmx:afterSettle", restoreState);
})();
