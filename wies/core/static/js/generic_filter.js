
// Filter Modal Functions
function openFilterModal() {
  const modal = document.getElementById('filterModal');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function closeFilterModal() {
  const modal = document.getElementById('filterModal');
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
}

function applyFiltersInstant() {
  const form = document.getElementById('modalFilterForm');
  const mainForm = document.querySelector('.rvo-form');

  // Copy values from modal form to main form
  const modalInputs = form.querySelectorAll('select, input');
  modalInputs.forEach(input => {
    const requireBoth = input.dataset.requireBoth === 'true';
    const combinedName = input.dataset.combinedName;

    let hiddenName;
    let hiddenValue;
    if (requireBoth && combinedName) {
      // Handle date range inputs that require both dates
      
      const fromInput = form.querySelector(`input[name="${combinedName}_from"]`);
      const toInput = form.querySelector(`input[name="${combinedName}_to"]`);
      const validationMessage = document.getElementById(`${combinedName}-validation-message`);

      const fromValue = fromInput ? fromInput.value : '';
      const toValue = toInput ? toInput.value : '';

      if (validationMessage) {
        // Show/hide validation message
        if ((fromValue && !toValue) || (!fromValue && toValue)) {
          validationMessage.style.display = 'block';
        } else {
          validationMessage.style.display = 'none';
        }

        // If both dates are provided, create combined parameter
        let combinedValue
        if (fromValue && toValue) {
          combinedValue = `${fromValue}_${toValue}`;        
        } else {
          combinedValue = ''
        }

        hiddenName = combinedName
        hiddenValue = combinedValue  
      }
    } else {
      // single value
      hiddenName = input.name
      hiddenValue = input.value
    }

    if (hiddenValue) {
      // Create or update hidden input for this filter
      let hiddenInput = mainForm.querySelector(`input[name="${hiddenName}"]`);
      if (!hiddenInput) {
        hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = hiddenName;
        mainForm.appendChild(hiddenInput);
      }
      hiddenInput.value = hiddenValue;
    } else {
      // Remove hidden input if value is empty
      const hiddenInput = mainForm.querySelector(`input[name="${hiddenName}"]`);
      if (hiddenInput && hiddenInput.type === 'hidden') {
        hiddenInput.remove();
      }
    }
  });

  // Trigger HTMX request without closing modal
  htmx.trigger(mainForm, 'change');

  // Update filter indicator immediately
  setTimeout(updateFilterIndicator, 100);
}


function clearAllFilters() {
  const form = document.getElementById('modalFilterForm');
  const mainForm = document.querySelector('.rvo-form');
  
  // Clear modal form
  form.querySelectorAll('select, input[type="date"]').forEach(input => {
    input.value = '';
  });
  
  // Remove all hidden filter inputs from main form
  mainForm.querySelectorAll('input[type="hidden"]').forEach(input => {
    input.remove();
  });
  
  // Trigger HTMX request
  htmx.trigger(mainForm, 'change');
  
  closeFilterModal();
}

// Update filter indicator
function updateFilterIndicator() {
  const filterButton = document.querySelector('.filter-button-container button');
  const filterText = document.querySelector('.filter-text');
  const mainForm = document.querySelector('.rvo-form');
  
  if (filterButton && filterText && mainForm) {
    // Count active filters from modal form inputs
    const activeFilters = Array.from(mainForm.querySelectorAll('input[type="hidden"]'))
      .length;
    
    // Update only the text span, keeping the icon intact
    if (activeFilters > 0) {
      filterText.textContent = `Filters (${activeFilters})`;
      filterButton.classList.add('utrecht-button--active');
    } else {
      filterText.textContent = 'Filters';
      filterButton.classList.remove('utrecht-button--active');
    }
  }
}

// Global HTMX event listener to update filter indicator
document.body.addEventListener('htmx:afterRequest', function(event) {
  updateFilterIndicator();
});

// Close modal with escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && document.getElementById('filterModal').style.display === 'flex') {
    closeFilterModal();
  }
});

// Close modal when clicking outside
document.getElementById('filterModal').addEventListener('click', function(e) {
  if (e.target === this) {
    closeFilterModal();
  }
});
