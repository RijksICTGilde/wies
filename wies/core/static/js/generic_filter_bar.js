// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
  const modal = document.getElementById('filterModal');
  const filterButton = document.querySelector('.filter-button');
  const closeButton = document.querySelector('.modal-close');
  const closeModalButton = document.querySelector('.close-modal-button');
  const clearFiltersButton = document.querySelector('.clear-filters-button');
  const form = document.querySelector('.rvo-form');

  if (!modal || !form) return;

  // Open modal
  if (filterButton) {
    filterButton.addEventListener('click', function() {
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    });
  }

  // Close modal function
  function closeFilterModal() {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }

  // Close button handlers
  if (closeButton) {
    closeButton.addEventListener('click', closeFilterModal);
  }
  if (closeModalButton) {
    closeModalButton.addEventListener('click', closeFilterModal);
  }

  // Close modal when clicking outside
  modal.addEventListener('click', function(e) {
    if (e.target === modal) {
      closeFilterModal();
    }
  });

  // Close modal with escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.style.display === 'flex') {
      closeFilterModal();
    }
  });

  // Handle date range validation and combined parameter submission
  const dateRangeInputs = document.querySelectorAll('input[type="date"]');

  dateRangeInputs.forEach(input => {
    input.addEventListener('change', function() {
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
        } else {
          // Clear value (but keep name attribute)
          hiddenOutput.value = '';
        }
      }
    });
  });

  // Clear all filters
  if (clearFiltersButton) {
    clearFiltersButton.addEventListener('click', function() {
      // Clear all filter inputs
      form.querySelectorAll('[data-filter-input]').forEach(input => {
        if (input.tagName === 'SELECT') {
          input.selectedIndex = 0;
        } else if (input.type === 'hidden') {
          input.value = '';
        }
      });

      // Clear date range inputs
      form.querySelectorAll('.date-range-input').forEach(input => {
        input.value = '';
      });

      // Clear search field
      const searchInput = form.querySelector('#search');
      if (searchInput) {
        searchInput.value = '';
      }

      // Clear validation messages
      document.querySelectorAll('.date-range-validation-message').forEach(msg => {
        msg.style.display = 'none';
      });

      // Trigger form submission via HTMX
      htmx.trigger(form, 'change');

      closeFilterModal();
    });
  }

  // Update filter count indicator
  function updateFilterIndicator() {
    if (!filterButton) return;

    const filterText = filterButton.querySelector('.filter-text');
    if (!filterText) return;

    let activeFilters = 0;

    // Count active filters
    form.querySelectorAll('[data-filter-input]').forEach(input => {
      if (input.value !== '') {
        activeFilters++;
      }
    });

    // Update button text and state
    if (activeFilters > 0) {
      filterText.textContent = `Filters (${activeFilters})`;
      filterButton.classList.add('utrecht-button--active');
    } else {
      filterText.textContent = 'Filters';
      filterButton.classList.remove('utrecht-button--active');
    }
  }

  // Update filter indicator after HTMX requests
  document.body.addEventListener('htmx:afterSwap', updateFilterIndicator);
  document.body.addEventListener('htmx:afterSettle', updateFilterIndicator);

  // Initial update
  updateFilterIndicator();
});
