// "Categorieën beheren"-sheet: rijen bijmaken en weer weghalen zonder de server.
//
// De formset rendert alleen de bestaande categorieën (extra=0). Een nieuwe rij
// is een kloon van het sjabloon waarin __prefix__ het volgende indexnummer
// wordt; TOTAL_FORMS gaat mee omhoog, zodat Django de rij als nieuw object
// ziet. Lege rijen slaat de formset zelf over.
//
// Verwijderen geldt alleen voor nog niet opgeslagen rijen: die staan altijd
// ACHTER de bestaande, dus na het weghalen hernummeren we alleen die staart.
// De bestaande rijen houden hun index, want een modelformset koppelt de eerste
// INITIAL_FORMS formulieren op volgorde aan de queryset — een bestaande rij naar
// een extra-slot verschuiven zou hem als nieuw object opslaan.
(function () {
  function wire(form) {
    if (!form || form.dataset.categoryManageWired) return;
    form.dataset.categoryManageWired = "true";

    const sheet = form.closest("nldd-sheet") || document;
    const template = sheet.querySelector("[data-category-row-template]");
    const totalForms = form.querySelector("[name$='-TOTAL_FORMS']");
    const initialForms = form.querySelector("[name$='-INITIAL_FORMS']");
    const addButton = form.querySelector("[data-add-category]");
    if (!template || !totalForms || !initialForms || !addButton) return;

    const addRow = addButton.closest("nldd-list-item");
    const initialCount = parseInt(initialForms.value, 10) || 0;

    function renumberNewRows() {
      const rows = form.querySelectorAll("[data-category-row]");
      rows.forEach(function (row, index) {
        if (index < initialCount) return;
        row.querySelectorAll("[name]").forEach(function (field) {
          field.setAttribute(
            "name",
            field
              .getAttribute("name")
              .replace(/^form-\d+-/, "form-" + index + "-"),
          );
        });
      });
      totalForms.value = String(rows.length);
    }

    addButton.addEventListener("click", function () {
      const index = parseInt(totalForms.value, 10) || 0;
      const holder = document.createElement("div");
      holder.innerHTML = template.innerHTML.replace(
        /__prefix__/g,
        String(index),
      );
      const row = holder.firstElementChild;
      addRow.parentNode.insertBefore(row, addRow);
      totalForms.value = String(index + 1);
      const field = row.querySelector("nldd-text-field");
      if (field && typeof field.focus === "function") field.focus();
    });

    // Een bestaande categorie leeghalen is geen manier om hem te verwijderen —
    // daar is de prullenbak voor. Verlaat je het veld leeg, dan komt de oude
    // naam terug, zodat het formulier altijd op te slaan is.
    form.querySelectorAll("[data-category-row]").forEach(function (row, index) {
      if (index >= initialCount) return;
      const field = row.querySelector("nldd-text-field");
      if (!field) return;
      const original = field.value;
      field.addEventListener("blur", function () {
        if (!(field.value || "").trim()) field.value = original;
      });
    });

    form.addEventListener("click", function (e) {
      const remove = e.composedPath().find(function (el) {
        return el.hasAttribute && el.hasAttribute("data-remove-new-category");
      });
      if (!remove) return;
      const row = remove.closest("[data-category-row]");
      if (!row) return;
      row.remove();
      renumberNewRows();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wire(document.querySelector("[data-category-manage-form]"));
  });

  // De sheet komt binnen via htmx, dus na elke swap opnieuw kijken.
  document.addEventListener("htmx:afterSwap", function (e) {
    const form =
      e.detail.target.querySelector &&
      e.detail.target.querySelector("[data-category-manage-form]");
    wire(form);
  });
})();
