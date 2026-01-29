// Shared filter utility functions

// Remove a single filter by name/type/value
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
    // For multi-select (label filters), find the correct dropdown
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

  // Trigger HTMX form submission
  htmx.trigger(form, "change");
}

// Clear all filters in a form
function clearAllFilters(formSelector) {
  const form = document.querySelector(formSelector);
  if (!form) return;

  // Clear all filter inputs
  form.querySelectorAll("[data-filter-input]").forEach((input) => {
    if (input.tagName === "SELECT") {
      input.selectedIndex = 0;
    } else if (input.type === "hidden") {
      input.value = "";
    }
  });

  // Clear date range inputs
  form.querySelectorAll('input[type="date"]').forEach((input) => {
    input.value = "";
  });

  // Clear search field
  const searchInput = form.querySelector("#search");
  if (searchInput) {
    searchInput.value = "";
  }

  // Clear validation messages
  document.querySelectorAll(".date-range-validation-message").forEach((msg) => {
    msg.style.display = "none";
  });

  // Trigger form submission via HTMX
  htmx.trigger(form, "change");
}

// Setup date range validation and combined value handling
function setupDateRangeListeners(formSelector) {
  const form = document.querySelector(formSelector);
  if (!form) return;

  const dateRangeInputs = form.querySelectorAll('input[type="date"]');

  dateRangeInputs.forEach((input) => {
    input.addEventListener("change", function (event) {
      event.stopPropagation(); // Prevent htmx from triggering on individual date changes

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

        // Show/hide validation message
        if (validationMessage) {
          if ((fromValue && !toValue) || (!fromValue && toValue)) {
            validationMessage.style.display = "block";
          } else {
            validationMessage.style.display = "none";
          }
        }

        // Update hidden output field
        if (fromValue && toValue) {
          // Both dates provided - set combined value
          hiddenOutput.value = `${fromValue}_${toValue}`;
          // Trigger htmx now that we have a valid range
          htmx.trigger(form, "change");
        } else {
          // Clear value (but keep name attribute)
          hiddenOutput.value = "";
        }
      }
    });
  });
}

// Handle back button navigation - reload page to sync filters with URL
function setupPopstateHandler() {
  window.addEventListener("popstate", function () {
    window.location.href = window.location.href;
  });
}
