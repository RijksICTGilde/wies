(function () {
  const checkbox = document.getElementById("placement-inherit-period");
  if (!checkbox) return;

  // Scoped to the period body, not the surrounding form: the form element is
  // owned by the generic inline-edit wrapper and carries no period data.
  const root = checkbox.closest("[data-placement-period]");
  if (!root) return;

  const hiddenSelect = root.querySelector("[data-period-source]");
  const serviceStart = root.dataset.serviceStart || null;
  const serviceEnd = root.dataset.serviceEnd || null;
  const startInput = root.querySelector("[data-specific-start]");
  const endInput = root.querySelector("[data-specific-end]");

  function update() {
    const inherit = checkbox.checked;
    hiddenSelect.value = inherit ? "SERVICE" : "PLACEMENT";
    startInput.disabled = inherit;
    endInput.disabled = inherit;
    if (inherit) {
      startInput.value = serviceStart ?? "";
      endInput.value = serviceEnd ?? "";
    }
  }

  checkbox.addEventListener("change", update);
  update();
})();
