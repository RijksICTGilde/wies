// Shared filter utility functions

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
  window.addEventListener("popstate", function (event) {
    window.location.href = window.location.href;
  });
}
