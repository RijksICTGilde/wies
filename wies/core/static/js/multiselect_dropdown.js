// Multiselect Dropdown Component
(function () {
  // Track which dropdown is open so we can restore it after HTMX swap
  var openDropdownId = null;
  var openDropdownSearch = "";

  function initMultiselects() {
    document.querySelectorAll("[data-multiselect]").forEach(initMultiselect);
  }

  function initMultiselect(container) {
    if (container.dataset.multiselectInit) return;
    container.dataset.multiselectInit = "true";

    var trigger = container.querySelector(".multiselect__trigger");
    var dropdown = container.querySelector(".multiselect__dropdown");
    var checkboxes = container.querySelectorAll(".multiselect__checkbox");
    var hiddenContainer = container.querySelector(
      ".multiselect__hidden-inputs",
    );
    var name = container.dataset.name;

    if (!trigger || !dropdown || !hiddenContainer) return;

    // Toggle dropdown
    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var isOpen = !dropdown.hidden;

      // Close all other multiselects first
      document.querySelectorAll("[data-multiselect]").forEach(function (other) {
        if (other !== container) closeDropdown(other);
      });

      if (isOpen) {
        closeDropdown(container);
      } else {
        dropdown.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
      }
    });

    // Search filtering
    var searchInput = container.querySelector(".multiselect__search");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        var query = searchInput.value.toLowerCase();
        container
          .querySelectorAll(".multiselect__option")
          .forEach(function (option) {
            var label = option
              .querySelector(".rvo-text")
              .textContent.toLowerCase();
            option.style.display = label.includes(query) ? "" : "none";
          });
      });
      // Prevent search events from bubbling to form
      searchInput.addEventListener("keydown", function (e) {
        e.stopPropagation();
      });
      searchInput.addEventListener("change", function (e) {
        e.stopPropagation();
      });
    }

    // Checkbox change: sync state and trigger HTMX immediately (for chips)
    checkboxes.forEach(function (cb) {
      cb.addEventListener("change", function (e) {
        e.stopPropagation(); // We'll trigger HTMX ourselves after syncing
        syncHiddenInputs(container, name, hiddenContainer);
        updateTriggerText(container, trigger);
        // Save open state before HTMX swaps the DOM
        saveOpenState(container);
        triggerFormChange(container);
      });
    });
  }

  function closeDropdown(container) {
    var dropdown = container.querySelector(".multiselect__dropdown");
    var trigger = container.querySelector(".multiselect__trigger");
    var searchInput = container.querySelector(".multiselect__search");
    if (dropdown) dropdown.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    if (searchInput) {
      searchInput.value = "";
      container
        .querySelectorAll(".multiselect__option")
        .forEach(function (opt) {
          opt.style.display = "";
        });
    }
  }

  function saveOpenState(container) {
    var trigger = container.querySelector(".multiselect__trigger");
    var searchInput = container.querySelector(".multiselect__search");
    openDropdownId = trigger ? trigger.getAttribute("aria-labelledby") : null;
    openDropdownSearch = searchInput ? searchInput.value : "";
  }

  function restoreOpenState() {
    if (!openDropdownId) return;
    var trigger = document.querySelector(
      '[aria-labelledby="' + openDropdownId + '"]',
    );
    if (!trigger) return;
    var container = trigger.closest("[data-multiselect]");
    if (!container) return;

    var dropdown = container.querySelector(".multiselect__dropdown");
    var searchInput = container.querySelector(".multiselect__search");
    if (dropdown) dropdown.hidden = false;
    trigger.setAttribute("aria-expanded", "true");

    // Restore search and re-filter
    if (searchInput && openDropdownSearch) {
      searchInput.value = openDropdownSearch;
      searchInput.dispatchEvent(new Event("input"));
    }

    openDropdownId = null;
    openDropdownSearch = "";
  }

  function syncHiddenInputs(container, name, hiddenContainer) {
    hiddenContainer.innerHTML = "";
    container
      .querySelectorAll(".multiselect__checkbox:checked")
      .forEach(function (cb) {
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = cb.value;
        input.setAttribute("data-filter-input", "");
        hiddenContainer.appendChild(input);
      });
  }

  function updateTriggerText(container, trigger) {
    var count = container.querySelectorAll(
      ".multiselect__checkbox:checked",
    ).length;
    var textEl = trigger.querySelector(".multiselect__trigger-text");
    if (textEl) {
      textEl.textContent = count > 0 ? count + " geselecteerd" : "";
    }
  }

  function triggerFormChange(container) {
    var form = container.closest("form");
    if (form && typeof htmx !== "undefined") {
      htmx.trigger(form, "change");
    }
  }

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-multiselect]")) {
      document.querySelectorAll("[data-multiselect]").forEach(closeDropdown);
    }
  });

  // Close on Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll("[data-multiselect]").forEach(closeDropdown);
    }
  });

  // Public API for chip removal
  window.multiselectUncheck = function (filterName, filterValue) {
    document
      .querySelectorAll('[data-multiselect][data-name="' + filterName + '"]')
      .forEach(function (container) {
        var cb = container.querySelector(
          '.multiselect__checkbox[value="' + filterValue + '"]',
        );
        if (cb) {
          cb.checked = false;
          var hiddenContainer = container.querySelector(
            ".multiselect__hidden-inputs",
          );
          syncHiddenInputs(container, filterName, hiddenContainer);
          updateTriggerText(
            container,
            container.querySelector(".multiselect__trigger"),
          );
        }
      });
  };

  // Public API for clearing all multiselects
  window.multiselectClearAll = function (form) {
    (form || document)
      .querySelectorAll("[data-multiselect]")
      .forEach(function (container) {
        container
          .querySelectorAll(".multiselect__checkbox")
          .forEach(function (cb) {
            cb.checked = false;
          });
        var hiddenContainer = container.querySelector(
          ".multiselect__hidden-inputs",
        );
        syncHiddenInputs(container, container.dataset.name, hiddenContainer);
        updateTriggerText(
          container,
          container.querySelector(".multiselect__trigger"),
        );
      });
  };

  // Initialize on DOM ready
  document.addEventListener("DOMContentLoaded", initMultiselects);

  // Re-initialize after HTMX swaps and restore open dropdown
  document.addEventListener("htmx:afterSwap", function () {
    initMultiselects();
    restoreOpenState();
  });
})();
