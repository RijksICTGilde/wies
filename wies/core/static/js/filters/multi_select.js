// Multi-select component
(function () {
  var openDropdownId = null;

  function positionDropdown(trigger, dropdown) {
    var rect = trigger.getBoundingClientRect();
    dropdown.style.top = rect.bottom + "px";
    dropdown.style.left = rect.left + "px";
    dropdown.style.width = rect.width + "px";
  }

  function syncState(container) {
    var name = container.dataset.name;
    var trigger = container.querySelector(".multiselect__trigger");
    var hiddenContainer = container.querySelector(
      ".multiselect__hidden-inputs",
    );
    if (!trigger || !hiddenContainer) return;

    hiddenContainer.innerHTML = "";
    var checked = container.querySelectorAll(".multiselect__checkbox:checked");
    checked.forEach(function (cb) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = cb.value;
      input.setAttribute("data-filter-input", "");
      hiddenContainer.appendChild(input);
    });

    var textEl = trigger.querySelector(".multiselect__trigger-text");
    if (textEl) {
      if (checked.length === 1) {
        var label = checked[0]
          .closest(".multiselect__option")
          .querySelector(".rvo-text");
        textEl.textContent = label ? label.textContent : "1 geselecteerd";
      } else {
        textEl.textContent =
          checked.length > 1 ? checked.length + " geselecteerd" : "";
      }
    }

    var clearBtn = container.querySelector(".multiselect__clear");
    if (clearBtn) clearBtn.hidden = checked.length === 0;
  }

  function closeDropdown(container) {
    var dropdown = container.querySelector(".multiselect__dropdown");
    var trigger = container.querySelector(".multiselect__trigger");
    if (dropdown) dropdown.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  }

  function onSelectionChange(container) {
    syncState(container);
    // Save open state so it survives HTMX DOM swap, then trigger swap
    var trigger = container.querySelector(".multiselect__trigger");
    openDropdownId = trigger ? trigger.getAttribute("aria-labelledby") : null;
    var form = container.closest("form");
    if (form && typeof htmx !== "undefined") htmx.trigger(form, "change");
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
    if (dropdown) {
      dropdown.hidden = false;
      positionDropdown(trigger, dropdown);
    }
    trigger.setAttribute("aria-expanded", "true");
    openDropdownId = null;
  }

  function initMultiselect(container) {
    if (container.dataset.multiselectInit) return;
    container.dataset.multiselectInit = "true";

    var trigger = container.querySelector(".multiselect__trigger");
    var dropdown = container.querySelector(".multiselect__dropdown");
    if (!trigger || !dropdown) return;

    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var isOpen = !dropdown.hidden;

      document.querySelectorAll("[data-multiselect]").forEach(function (other) {
        if (other !== container) closeDropdown(other);
      });

      if (isOpen) {
        closeDropdown(container);
      } else {
        dropdown.hidden = false;
        positionDropdown(trigger, dropdown);
        trigger.setAttribute("aria-expanded", "true");
      }
    });

    var clearButton = container.querySelector(".multiselect__clear");
    if (clearButton) {
      clearButton.addEventListener("click", function (e) {
        e.stopPropagation();
        container
          .querySelectorAll(".multiselect__checkbox")
          .forEach(function (cb) {
            cb.checked = false;
          });
        onSelectionChange(container);
      });
    }

    container.querySelectorAll(".multiselect__checkbox").forEach(function (cb) {
      cb.addEventListener("change", function (e) {
        e.stopPropagation();
        onSelectionChange(container);
      });
    });
  }

  // Global: close on outside click
  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-multiselect]")) {
      document.querySelectorAll("[data-multiselect]").forEach(closeDropdown);
    }
  });

  // Global: close on Escape (capture to prevent modal from closing)
  document.addEventListener(
    "keydown",
    function (e) {
      if (e.key !== "Escape") return;
      var open = document.querySelectorAll(
        "[data-multiselect] .multiselect__dropdown:not([hidden])",
      );
      if (open.length > 0) {
        e.stopPropagation();
        e.preventDefault();
        document.querySelectorAll("[data-multiselect]").forEach(closeDropdown);
      }
    },
    true,
  );

  // Global: reposition on scroll (fixed dropdown must follow trigger)
  document.addEventListener(
    "scroll",
    function () {
      document
        .querySelectorAll(
          "[data-multiselect] .multiselect__dropdown:not([hidden])",
        )
        .forEach(function (dropdown) {
          var trigger = dropdown
            .closest("[data-multiselect]")
            .querySelector(".multiselect__trigger");
          if (trigger) positionDropdown(trigger, dropdown);
        });
    },
    true,
  );

  // Public API
  window.multiselectUncheck = function (name, value) {
    var container = document.querySelector(
      '[data-multiselect][data-name="' + name + '"]',
    );
    if (!container) return;
    var cb = container.querySelector(
      '.multiselect__checkbox[value="' + value + '"]',
    );
    if (cb) {
      cb.checked = false;
      syncState(container);
    }
  };

  window.multiselectClearAll = function (scope) {
    (scope || document)
      .querySelectorAll("[data-multiselect]")
      .forEach(function (container) {
        container
          .querySelectorAll(".multiselect__checkbox")
          .forEach(function (cb) {
            cb.checked = false;
          });
        syncState(container);
      });
  };

  // Init
  function initAll() {
    document.querySelectorAll("[data-multiselect]").forEach(initMultiselect);
  }

  document.addEventListener("DOMContentLoaded", initAll);
  document.addEventListener("htmx:afterSwap", function () {
    initAll();
    restoreOpenState();
  });
})();
