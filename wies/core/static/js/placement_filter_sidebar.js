// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
  // ============================================================================
  // FILTER MANAGEMENT FUNCTIONS
  // ============================================================================

  function removeFilter(filterName, filterType, filterValue) {
    const form = document.querySelector('.filter-sidebar-form');
    if (!form) return;

    if (filterType === 'zoek') {
      const searchInput = document.querySelector('#search');
      if (searchInput) {
        searchInput.value = '';
      }
    } else if (filterType === 'select') {
      const selectElement = form.querySelector(`[name="${filterName}"]`);
      if (selectElement) {
        selectElement.selectedIndex = 0;
      }
    } else if (filterType === 'select-multi') {
      // For multi-select (label filters), find the correct dropdown
      // There are multiple <select name="label"> elements (one per category)
      const selectElements = form.querySelectorAll(`[name="${filterName}"]`);
      selectElements.forEach(selectElement => {
        for (let i = 0; i < selectElement.options.length; i++) {
          if (selectElement.options[i].value === filterValue) {
            selectElement.selectedIndex = 0;
            return;
          }
        }
      });
    } else if (filterType === 'date_range') {
      const fromInput = document.getElementById(`filter-${filterName}-from`);
      const toInput = document.getElementById(`filter-${filterName}-to`);
      const hiddenInput = document.getElementById(`filter-${filterName}-combined`);
      const validationMessage = document.getElementById(`${filterName}-validation-message`);

      if (fromInput) fromInput.value = '';
      if (toInput) toInput.value = '';
      if (hiddenInput) hiddenInput.value = '';
      if (validationMessage) validationMessage.style.display = 'none';
    }

    // Trigger HTMX form submission
    htmx.trigger(form, 'change');
  }

  // ============================================================================
  // EVENT DELEGATION - All click handlers
  // ============================================================================

  document.addEventListener('click', function(e) {
    // Filter chip removal
    if (e.target.closest('.filter-chip-remove')) {
      e.preventDefault();
      const button = e.target.closest('.filter-chip-remove');
      const filterName = button.dataset.filterName;
      const filterValue = button.dataset.filterValue;
      const chip = button.closest('.filter-chip');
      const filterType = chip.dataset.filterType;

      removeFilter(filterName, filterType, filterValue);
    }
  });

  // ============================================================================
  // DATE RANGE VALIDATION AND SETUP
  // ============================================================================

  function setupDateRangeListeners() {
    const form = document.querySelector('.filter-sidebar-form');
    if (!form) return;

    const dateRangeInputs = document.querySelectorAll('input[type="date"]');

    dateRangeInputs.forEach(input => {
      input.addEventListener('change', function(event) {
        event.stopPropagation(); // Prevent htmx from triggering on individual date changes

        const requireBoth = input.dataset.requireBoth === 'true';
        const combinedName = input.dataset.combinedName;
        const pairId = input.dataset.pairId;

        if (requireBoth && combinedName && pairId) {
          const pairInput = document.getElementById(pairId);
          const validationMessage = document.getElementById(`${combinedName}-validation-message`);
          const hiddenOutput = form.querySelector(`input[name="${combinedName}"]`);

          if (!pairInput || !hiddenOutput) return;

          const fromInput = input.id.includes('-from') ? input : pairInput;
          const toInput = input.id.includes('-to') ? input : pairInput;

          const fromValue = fromInput.value;
          const toValue = toInput.value;

          // Show/hide validation message
          if (validationMessage) {
            if ((fromValue && !toValue) || (!fromValue && toValue)) {
              validationMessage.style.display = 'block';
            } else {
              validationMessage.style.display = 'none';
            }
          }

          // Update hidden output field
          if (fromValue && toValue) {
            // Both dates provided - set combined value
            hiddenOutput.value = `${fromValue}_${toValue}`;
            // Trigger htmx now that we have a valid range
            htmx.trigger(form, 'change');
          } else {
            // Clear value (but keep name attribute)
            hiddenOutput.value = '';
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

  // Listen for HTMX afterSwap event to re-initialize after content swap
  document.body.addEventListener('htmx:afterSwap', function(event) {
    // Only restore if the swap target was the filter container
    if (event.detail.target.id === 'filter-and-table-container') {
      setupDateRangeListeners(); // Re-attach date range listeners to new elements
    }
  });

  // Handle back button navigation - reload page to sync filters with URL
  window.addEventListener('popstate', function(event) {
    window.location.href = window.location.href;
  });
});
