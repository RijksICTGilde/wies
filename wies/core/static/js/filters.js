// Filter functionality for all pages
// Handles: chip removal, date range validation, filter modal, filter sidebar

function toggleFilters() {
  const layout = document.getElementById("layout");

  // Toggle both classes - CSS media queries determine which one takes effect
  layout.classList.toggle("layout--collapsed");
  layout.classList.toggle("layout--mobile-filters-open");

  // Persist sidebar state in URL (only relevant for desktop, harmless on mobile)
  const url = new URL(window.location);
  if (layout.classList.contains("layout--collapsed")) {
    url.searchParams.set("filters", "0");
  } else {
    url.searchParams.delete("filters");
  }
  history.replaceState({}, "", url);
}

// ============================================================================
// Shared utilities
// ============================================================================

function removeFilter(formSelector, filterName, filterType, filterValue) {
  const form = document.querySelector(formSelector);
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
  }

  htmx.trigger(form, "change");
}

function clearAllFilters(formSelector) {
  const form = document.querySelector(formSelector);
  if (!form) return;

  form.querySelectorAll("[data-filter-input]").forEach((input) => {
    if (input.tagName === "SELECT") {
      input.selectedIndex = 0;
    } else if (input.type === "hidden") {
      input.value = "";
    }
  });

  form.querySelectorAll('input[type="date"]').forEach((input) => {
    input.value = "";
  });

  const searchInput = form.querySelector("#search");
  if (searchInput) {
    searchInput.value = "";
  }

  document.querySelectorAll(".date-range-validation-message").forEach((msg) => {
    msg.style.display = "none";
  });

  htmx.trigger(form, "change");
}

function setupDateRangeListeners(formSelector) {
  const form = document.querySelector(formSelector);
  if (!form) return;

  form.querySelectorAll('input[type="date"]').forEach((input) => {
    input.addEventListener("change", function (event) {
      event.stopPropagation();

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

        if (validationMessage) {
          if ((fromValue && !toValue) || (!fromValue && toValue)) {
            validationMessage.style.display = "block";
          } else {
            validationMessage.style.display = "none";
          }
        }

        if (fromValue && toValue) {
          hiddenOutput.value = `${fromValue}_${toValue}`;
          htmx.trigger(form, "change");
        } else {
          hiddenOutput.value = "";
        }
      }
    });
  });
}

// ============================================================================
// Page initialization
// ============================================================================

document.addEventListener("DOMContentLoaded", function () {
  // Handle back button navigation - reload page to sync filters with URL
  window.addEventListener("popstate", function () {
    window.location.href = window.location.href;
  });

  // --------------------------------------------------------------------------
  // Filter sidebar (placements page)
  // --------------------------------------------------------------------------
  const sidebarForm = document.querySelector(".filter-sidebar-form");
  if (sidebarForm) {
    const sidebarFormSelector = ".filter-sidebar-form";

    // Filter chip removal via event delegation
    document.addEventListener("click", function (e) {
      if (e.target.closest(".filter-chip-remove")) {
        e.preventDefault();
        const button = e.target.closest(".filter-chip-remove");
        const chip = button.closest(".filter-chip");
        removeFilter(
          sidebarFormSelector,
          button.dataset.filterName,
          chip.dataset.filterType,
          button.dataset.filterValue,
        );
      }
    });

    setupDateRangeListeners(sidebarFormSelector);

    document.body.addEventListener("htmx:afterSwap", function (event) {
      if (event.detail.target.id === "filter-and-table-container") {
        setupDateRangeListeners(sidebarFormSelector);
      }
    });
  }

  // --------------------------------------------------------------------------
  // Filter modal (generic filter bar, e.g. user admin page)
  // --------------------------------------------------------------------------
  const modal = document.getElementById("filterModal");
  const filterButton = document.querySelector(".filter-button");
  const form = document.querySelector(".rvo-form");

  if (modal && form) {
    const formSelector = ".rvo-form";

    function closeFilterModal() {
      modal.style.display = "none";
      document.body.style.overflow = "auto";
    }

    if (filterButton) {
      filterButton.addEventListener("click", function () {
        modal.style.display = "flex";
        document.body.style.overflow = "hidden";
      });
    }

    const closeButton = document.querySelector(".modal-close");
    if (closeButton) {
      closeButton.addEventListener("click", closeFilterModal);
    }

    const closeModalButton = document.querySelector(".close-modal-button");
    if (closeModalButton) {
      closeModalButton.addEventListener("click", closeFilterModal);
    }

    modal.addEventListener("click", function (e) {
      if (e.target === modal) {
        closeFilterModal();
      }
    });

    setupDateRangeListeners(formSelector);

    const clearFiltersButton = document.querySelector(".clear-filters-button");
    if (clearFiltersButton) {
      clearFiltersButton.addEventListener("click", function () {
        clearAllFilters(formSelector);
        closeFilterModal();
      });
    }

    // Update filter count indicator
    function updateFilterIndicator() {
      if (!filterButton) return;
      const filterText = filterButton.querySelector(".filter-text");
      if (!filterText) return;

      let activeFilters = 0;
      form.querySelectorAll("[data-filter-input]").forEach((input) => {
        if (input.value !== "" && input.value !== "0") {
          activeFilters++;
        }
      });

      if (activeFilters > 0) {
        filterText.textContent = `Filters (${activeFilters})`;
        filterButton.classList.add("utrecht-button--active");
      } else {
        filterText.textContent = "Filters";
        filterButton.classList.remove("utrecht-button--active");
      }
    }

    document.body.addEventListener("htmx:afterSwap", updateFilterIndicator);
    document.body.addEventListener("htmx:afterSettle", updateFilterIndicator);
    updateFilterIndicator();

    // Close on ESC
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.style.display === "flex") {
        closeFilterModal();
      }
    });
  }

  // ESC handler for mobile overlays (filters + menu)
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    const layout = document.getElementById("layout");
    if (layout && layout.classList.contains("layout--mobile-filters-open")) {
      layout.classList.remove("layout--mobile-filters-open");
      layout.classList.add("layout--collapsed");
      return;
    }
    const menubar = document.querySelector(".menubar");
    if (menubar && menubar.classList.contains("menubar--mobile-open")) {
      menubar.classList.remove("menubar--mobile-open");
    }
  });
});
