// Filter bar for user admin page (modal-based filters)
// Depends on: filter_utils.js

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("filterModal");
  const filterButton = document.querySelector(".filter-button");
  const closeButton = document.querySelector(".modal-close");
  const closeModalButton = document.querySelector(".close-modal-button");
  const clearFiltersButton = document.querySelector(".clear-filters-button");
  const form = document.querySelector(".rvo-form");

  if (!modal || !form) return;

  const formSelector = ".rvo-form";

  // Open modal
  if (filterButton) {
    filterButton.addEventListener("click", function () {
      modal.style.display = "flex";
      document.body.style.overflow = "hidden";
    });
  }

  // Close modal function
  function closeFilterModal() {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
  }

  // Close button handlers
  if (closeButton) {
    closeButton.addEventListener("click", closeFilterModal);
  }
  if (closeModalButton) {
    closeModalButton.addEventListener("click", closeFilterModal);
  }

  // Close modal when clicking outside
  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      closeFilterModal();
    }
  });

  // Handle date range validation
  setupDateRangeListeners(formSelector);

  // Clear all filters
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

    // Count active filters
    form.querySelectorAll("[data-filter-input]").forEach((input) => {
      if (input.value !== "" && input.value !== "0") {
        activeFilters++;
      }
    });

    // Update button text and state
    if (activeFilters > 0) {
      filterText.textContent = `Filters (${activeFilters})`;
      filterButton.classList.add("utrecht-button--active");
    } else {
      filterText.textContent = "Filters";
      filterButton.classList.remove("utrecht-button--active");
    }
  }

  // Update filter indicator after HTMX requests
  document.body.addEventListener("htmx:afterSwap", updateFilterIndicator);
  document.body.addEventListener("htmx:afterSettle", updateFilterIndicator);

  // Initial update
  updateFilterIndicator();

  // Handle back button navigation
  setupPopstateHandler();

  // Register ESC handler via overlay close registry (layout.js)
  registerOverlayClose(
    () => modal && modal.style.display === "flex",
    () => closeFilterModal(),
  );
});
