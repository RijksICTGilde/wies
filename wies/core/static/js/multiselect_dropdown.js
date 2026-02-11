// Multiselect Dropdown Component
(function () {
  function initMultiselects(root) {
    const containers = (root || document).querySelectorAll(
      "[data-multiselect]",
    );
    containers.forEach(initMultiselect);
  }

  function initMultiselect(container) {
    // Skip if already initialized
    if (container.dataset.multiselectInit) return;
    container.dataset.multiselectInit = "true";

    const trigger = container.querySelector(".multiselect__trigger");
    const dropdown = container.querySelector(".multiselect__dropdown");
    const checkboxes = container.querySelectorAll(".multiselect__checkbox");
    const hiddenContainer = container.querySelector(
      ".multiselect__hidden-inputs",
    );
    const name = container.dataset.name;

    if (!trigger || !dropdown || !hiddenContainer) return;

    // Toggle dropdown
    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = !dropdown.hidden;

      // Close all other multiselects first
      document.querySelectorAll("[data-multiselect]").forEach(function (other) {
        if (other !== container) {
          const otherDropdown = other.querySelector(".multiselect__dropdown");
          const otherTrigger = other.querySelector(".multiselect__trigger");
          if (otherDropdown) otherDropdown.hidden = true;
          if (otherTrigger) otherTrigger.setAttribute("aria-expanded", "false");
        }
      });

      if (isOpen) {
        closeDropdown(container);
      } else {
        dropdown.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
      }
    });

    // Search filtering
    const searchInput = container.querySelector(".multiselect__search");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        const query = searchInput.value.toLowerCase();
        container
          .querySelectorAll(".multiselect__option")
          .forEach(function (option) {
            const label = option
              .querySelector(".rvo-text")
              .textContent.toLowerCase();
            option.style.display = label.includes(query) ? "" : "none";
          });
      });
      // Prevent keystrokes from bubbling to form/closing dropdown
      searchInput.addEventListener("keydown", function (e) {
        e.stopPropagation();
      });
    }

    // Checkbox change handler — only sync state, don't trigger HTMX yet
    checkboxes.forEach(function (cb) {
      cb.addEventListener("change", function () {
        container.dataset.dirty = "true";
        syncHiddenInputs(container, name, hiddenContainer);
        updateTriggerText(container, trigger);
      });
    });
  }

  function closeDropdown(container) {
    const dropdown = container.querySelector(".multiselect__dropdown");
    const trigger = container.querySelector(".multiselect__trigger");
    const searchInput = container.querySelector(".multiselect__search");
    if (dropdown) dropdown.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    // Reset search filter
    if (searchInput) {
      searchInput.value = "";
      container
        .querySelectorAll(".multiselect__option")
        .forEach(function (opt) {
          opt.style.display = "";
        });
    }
    // Trigger HTMX only if selections changed
    if (container.dataset.dirty === "true") {
      container.dataset.dirty = "";
      triggerFormChange(container);
    }
  }

  function syncHiddenInputs(container, name, hiddenContainer) {
    // Clear existing hidden inputs
    hiddenContainer.innerHTML = "";

    // Create hidden input for each checked checkbox
    const checked = container.querySelectorAll(
      ".multiselect__checkbox:checked",
    );
    checked.forEach(function (cb) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = cb.value;
      input.setAttribute("data-filter-input", "");
      hiddenContainer.appendChild(input);
    });
  }

  function updateTriggerText(container, trigger) {
    const count = container.querySelectorAll(
      ".multiselect__checkbox:checked",
    ).length;
    const textEl = trigger.querySelector(".multiselect__trigger-text");
    if (textEl) {
      textEl.textContent = count > 0 ? count + " geselecteerd" : "";
    }
  }

  function triggerFormChange(container) {
    const form = container.closest("form");
    if (form && typeof htmx !== "undefined") {
      htmx.trigger(form, "change");
    }
  }

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-multiselect]")) {
      document
        .querySelectorAll("[data-multiselect]")
        .forEach(function (container) {
          closeDropdown(container);
        });
    }
  });

  // Close on Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document
        .querySelectorAll("[data-multiselect]")
        .forEach(function (container) {
          closeDropdown(container);
        });
    }
  });

  // Public API for chip removal integration
  window.multiselectUncheck = function (filterName, filterValue) {
    document
      .querySelectorAll('[data-multiselect][data-name="' + filterName + '"]')
      .forEach(function (container) {
        const cb = container.querySelector(
          '.multiselect__checkbox[value="' + filterValue + '"]',
        );
        if (cb) {
          cb.checked = false;
          const hiddenContainer = container.querySelector(
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

  // Public API for clearing all multiselects in a form
  window.multiselectClearAll = function (form) {
    const containers = (form || document).querySelectorAll(
      "[data-multiselect]",
    );
    containers.forEach(function (container) {
      container
        .querySelectorAll(".multiselect__checkbox")
        .forEach(function (cb) {
          cb.checked = false;
        });
      const hiddenContainer = container.querySelector(
        ".multiselect__hidden-inputs",
      );
      const name = container.dataset.name;
      syncHiddenInputs(container, name, hiddenContainer);
      updateTriggerText(
        container,
        container.querySelector(".multiselect__trigger"),
      );
    });
  };

  // Initialize on DOM ready
  document.addEventListener("DOMContentLoaded", function () {
    initMultiselects();
  });

  // Re-initialize after HTMX swaps
  document.addEventListener("htmx:afterSwap", function () {
    initMultiselects();
  });
})();
