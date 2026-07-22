// Koppelt de periodekeuze aan de datumvelden.
//
// Twee vormen, beide ondersteund:
//   - nldd-segmented-control[data-period-choice] (bewerkpaneel van de plaatsing)
//   - checkbox #placement-inherit-period         (generieke inline-edit form)
//
// Bij "van opdracht" verdwijnen de datumvelden en krijgen ze de periode van de
// opdracht; de verborgen period_source-select houdt de waarde bij die het
// formulier post. De velden blijven enabled zodat ze meeposten — met
// period_source=SERVICE gebruikt de server de opdrachtperiode toch.
//
// De switch [data-end-date-known] stuurt alleen het einddatumveld aan: uit
// betekent "loopt door", dus einddatum leeg. Hij post zelf niet mee.
(function () {
  const group = document.querySelector("[data-period-choice]");
  const checkbox = document.getElementById("placement-inherit-period");
  const control = group || checkbox;
  if (!control) return;

  const form = control.closest("form");
  if (!form) return;

  // Op name, niet op data-attributen: de widget-templates geven willekeurige
  // data-* niet door aan de NLDD-velden, dus die hooks komen nooit in de DOM.
  const hiddenSelect = form.querySelector("[name=period_source]");
  const serviceStart = form.dataset.serviceStart || null;
  const serviceEnd = form.dataset.serviceEnd || null;
  const startInput = form.querySelector("[name=specific_start_date]");
  const endInput = form.querySelector("[name=specific_end_date]");
  const endKnownSwitch = form.querySelector("[data-end-date-known]");
  const servicePeriodHelp = form.querySelector("[data-service-period-help]");

  // Het hele veld verbergen, niet alleen de input: anders blijft het label staan.
  // Zonder nldd-form-field (de oudere inline-edit form) valt het terug op de
  // input zelf.
  const fieldOf = (el) => el && (el.closest("nldd-form-field") || el);
  const startField = fieldOf(startInput);
  const endField = fieldOf(endInput);
  const endKnownField = fieldOf(endKnownSwitch);

  function inheritsFromService() {
    if (!group) return checkbox.checked;
    return group.getAttribute("value") !== "PLACEMENT";
  }

  function endDateKnown() {
    return !endKnownSwitch || endKnownSwitch.hasAttribute("checked");
  }

  // Onthoudt de laatst getoonde einddatum, zodat de switch uit- en weer aanzetten
  // hem niet wist. Bij "van opdracht" wordt het veld met de opdrachtperiode
  // gevuld; dat is niet de keuze van de gebruiker en slaan we dus niet op.
  let lastEndDate = endInput ? endInput.value : "";

  function update(inherit, knownOverride) {
    if (hiddenSelect) hiddenSelect.value = inherit ? "SERVICE" : "PLACEMENT";
    if (servicePeriodHelp) servicePeriodHelp.hidden = !inherit;
    if (startField) startField.hidden = inherit;
    if (endKnownField) endKnownField.hidden = inherit;
    // Einddatum verdwijnt óók als de gebruiker zegt dat er geen einddatum is.
    // knownOverride komt uit het change-event: het attribuut op de switch is op
    // dat moment nog niet bijgewerkt.
    const known = knownOverride === undefined ? endDateKnown() : knownOverride;
    if (endField) endField.hidden = inherit || !known;
    if (inherit) {
      if (startInput) startInput.value = serviceStart ?? "";
      if (endInput) endInput.value = serviceEnd ?? "";
    } else if (endInput) {
      // Leeg = "loopt door"; de ingevulde datum bewaren we voor als de switch
      // weer aangaat.
      if (!known) {
        if (endInput.value) lastEndDate = endInput.value;
        endInput.value = "";
      } else if (!endInput.value) {
        endInput.value = lastEndDate;
      }
    }
  }

  if (group) {
    // nldd-segmented-control bubbelt een change met detail.value.
    group.addEventListener("change", (e) => {
      const value = e.detail && e.detail.value;
      update(value ? value === "SERVICE" : inheritsFromService());
    });
  } else {
    checkbox.addEventListener("change", () => update(checkbox.checked));
  }

  if (endKnownSwitch) {
    endKnownSwitch.addEventListener("change", (e) => {
      const known = e.detail ? e.detail.checked : endDateKnown();
      update(inheritsFromService(), known);
    });
  }

  update(inheritsFromService());
})();
