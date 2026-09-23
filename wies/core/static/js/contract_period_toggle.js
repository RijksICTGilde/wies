// The "Einddatum is bekend" switch of the contract-period sheet: off means the
// period runs on, so the end date field is hidden and cleared. Same idea as the
// switch in period_fields.js, without the inherit logic that one carries.
(function () {
  function init(toggle) {
    if (toggle.dataset.contractEndInit) return;
    toggle.dataset.contractEndInit = "true";
    const form = toggle.closest("form");
    const endInput = form && form.querySelector("[name=end_date]");
    if (!endInput) return;
    // Hide the whole field, not just the input, or the label stays behind.
    const endField = endInput.closest("nldd-form-field") || endInput;
    let lastEndDate = endInput.value;
    toggle.addEventListener("change", (e) => {
      const known = e.detail ? e.detail.checked : toggle.hasAttribute("checked");
      endField.hidden = !known;
      if (!known) {
        if (endInput.value) lastEndDate = endInput.value;
        endInput.value = "";
      } else if (!endInput.value) {
        endInput.value = lastEndDate;
      }
    });
  }

  function scan(root) {
    (root || document).querySelectorAll("[data-contract-end-known]").forEach(init);
  }

  document.addEventListener("DOMContentLoaded", () => scan(document));
  document.addEventListener("htmx:afterSwap", (e) => scan(e.detail.target));
})();
