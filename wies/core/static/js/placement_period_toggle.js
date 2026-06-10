(function () {
  const checkbox = document.getElementById("placement-inherit-period");
  if (!checkbox) return;

  const form = checkbox.closest("form");
  const hiddenSelect = form.querySelector("[data-period-source]");
  const serviceStart = form.dataset.serviceStart || null;
  const serviceEnd = form.dataset.serviceEnd || null;
  const startInput = form.querySelector("[data-specific-start]");
  const endInput = form.querySelector("[data-specific-end]");

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
