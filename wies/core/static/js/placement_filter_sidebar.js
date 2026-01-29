// Filter sidebar for placements page (sidebar-based filters with chips)
// Depends on: filter_utils.js

document.addEventListener("DOMContentLoaded", function () {
  const formSelector = ".filter-sidebar-form";

  // Filter chip removal via event delegation
  document.addEventListener("click", function (e) {
    if (e.target.closest(".filter-chip-remove")) {
      e.preventDefault();
      const button = e.target.closest(".filter-chip-remove");
      const filterName = button.dataset.filterName;
      const filterValue = button.dataset.filterValue;
      const chip = button.closest(".filter-chip");
      const filterType = chip.dataset.filterType;

      removeFilter(formSelector, filterName, filterType, filterValue);
    }
  });

  // Setup date range listeners on initial load
  setupDateRangeListeners(formSelector);

  // Listen for HTMX afterSwap event to re-initialize after content swap
  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target.id === "filter-and-table-container") {
      setupDateRangeListeners(formSelector);
    }
  });

  // Handle back button navigation
  setupPopstateHandler();
});
