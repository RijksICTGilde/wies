// Checkbox filter component — inline checkboxes with toggle and counters
// Uses event delegation so listeners survive OOB swaps.
(function () {
  // Track which filter groups are manually expanded (survives OOB swaps)
  var expandedGroups = new Set();

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

  // Restore expanded state after OOB swap (for groups without selected extra options)
  function restoreExpandedState() {
    document
      .querySelectorAll("[data-checkbox-filter]")
      .forEach(function (container) {
        var key = getGroupKey(container);
        if (!expandedGroups.has(key)) return;
        var extra = container.querySelector(".checkbox-filter__options--extra");
        var toggle = container.querySelector(".checkbox-filter__toggle");
        if (extra && extra.hidden) {
          extra.hidden = false;
          if (toggle) {
            toggle.classList.add("checkbox-filter__toggle--expanded");
            var textEl = toggle.querySelector(".checkbox-filter__toggle-text");
            if (textEl) textEl.textContent = "Toon minder";
          }
        }
      });
  }

  // Checkbox change — capture phase to stopPropagation before form's hx-trigger fires
  document.addEventListener(
    "change",
    function (e) {
      if (!e.target.matches(".checkbox-filter__checkbox")) return;
      e.stopPropagation();
      var container = e.target.closest("[data-checkbox-filter]");
      if (!container) return;
      syncHiddenInputs(container);
      var form = container.closest("form");
      if (form && typeof htmx !== "undefined") {
        htmx.trigger(form, "change");
      }
    },
    true,
  ); // capture phase

  // Toggle section collapse via header chevron
  document.addEventListener("click", function (e) {
    var headerBtn = e.target.closest(".checkbox-filter__header");
    if (headerBtn) {
      e.preventDefault();
      var container = headerBtn.closest("[data-checkbox-filter]");
      if (!container) return;
      var body = container.querySelector(".checkbox-filter__body");
      if (!body) return;
      var isCollapsed = body.hidden;
      body.hidden = !isCollapsed;
      headerBtn.classList.toggle(
        "checkbox-filter__header--collapsed",
        isCollapsed,
      );
      return;
    }

    // Toggle "Toon meer"/"Toon minder" via event delegation
    var toggleBtn = e.target.closest(".checkbox-filter__toggle");
    if (!toggleBtn) return;
    e.preventDefault();
    var container = toggleBtn.closest("[data-checkbox-filter]");
    if (!container) return;
    var extraOptions = container.querySelector(
      ".checkbox-filter__options--extra",
    );
    if (!extraOptions) return;
    var isExpanded = !extraOptions.hidden;
    extraOptions.hidden = isExpanded;
    var textEl = toggleBtn.querySelector(".checkbox-filter__toggle-text");
    if (textEl) {
      textEl.textContent = isExpanded ? "Toon meer" : "Toon minder";
    }
    var iconEl = toggleBtn.querySelector(".checkbox-filter__toggle-icon");
    if (iconEl) {
      iconEl.textContent = isExpanded ? "+" : "\u2212";
    }
    toggleBtn.classList.toggle(
      "checkbox-filter__toggle--expanded",
      !isExpanded,
    );

    // Track expanded state
    var key = getGroupKey(container);
    if (isExpanded) {
      expandedGroups.delete(key);
    } else {
      expandedGroups.add(key);
    }
  });

  // Public API: uncheck a single value (used by chip removal)
  // Searches ALL containers with matching name (multiple categories share data-name="labels")
  window.checkboxFilterUncheck = function (name, value) {
    document
      .querySelectorAll('[data-checkbox-filter][data-name="' + name + '"]')
      .forEach(function (container) {
        var cb = container.querySelector(
          '.checkbox-filter__checkbox[value="' + value + '"]',
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
          .querySelectorAll(".checkbox-filter__checkbox")
          .forEach(function (cb) {
            cb.checked = false;
          });
        syncHiddenInputs(container);
      });
  };

  // Restore expanded state after OOB swap
  document.addEventListener("htmx:afterSettle", restoreExpandedState);
})();
