// Behaviour for inline-edit display partials.
//
// 1. Toast notification on successful save (listens for HX-Trigger: inline-edit-saved).
// 2. "Toon meer / Toon minder" toggle on long text fields.
// Both use delegated listeners that survive HTMX swaps.

function showSavedToast(label) {
  // nldd-notification plaatst zichzelf in de gedeelde regio en telt zelf af,
  // met een pauze bij hover of focus — vandaar geen container, geen timers en
  // geen top-layer-omweg meer. Waar we hem neerzetten doet er niet toe; hij
  // verhuist toch. ui_handlers.js haalt hem weg na `dismiss`.
  //
  // Eén melding, niet één per opgeslagen veld. Een scherm dat meerdere velden
  // achter elkaar bewaart (de onboarding-wizard slaat per veld en per opdracht
  // los op) zou anders een deck van identieke "Opgeslagen"-regels opbouwen.
  // De vorige vervangen laat de klok opnieuw lopen, zodat de laatste save de
  // melding is die je ziet.
  document
    .querySelectorAll("nldd-notification[data-wies-saved]")
    .forEach((el) => el.remove());

  const toast = document.createElement("nldd-notification");
  toast.setAttribute("variant", "success");
  // "Rol opgeslagen" zegt meer dan "Opgeslagen". Het label komt van de Editable
  // en begint met een hoofdletter ("Periode"), dus die blijft vooraan staan.
  toast.setAttribute(
    "text",
    label ? `${label} opgeslagen` : "Wijziging opgeslagen",
  );
  toast.setAttribute("data-wies-saved", "");
  document.body.appendChild(toast);
}

// Show toast after successful inline-edit save.
// The view sets HX-Trigger-After-Swap: inline-edit-saved on the response.
document.addEventListener("inline-edit-saved", (e) =>
  showSavedToast(e.detail?.label),
);

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".inline-edit-show-more");
  if (!toggle) return;

  const wrapper = toggle.parentElement;
  if (!wrapper) return;
  // Template uses `inline-edit-long-text__*` for the value spans; de knop zelf
  // is een nldd-button, dus tekst en icoon gaan via attributen.
  const truncated = wrapper.querySelector(".inline-edit-long-text__truncated");
  const full = wrapper.querySelector(".inline-edit-long-text__full");
  if (!truncated || !full) return;

  const expanded = full.hidden === false;
  truncated.hidden = !expanded;
  full.hidden = expanded;
  toggle.setAttribute("text", expanded ? "Toon meer" : "Toon minder");
  toggle.setAttribute("start-icon", expanded ? "chevron-down" : "chevron-up");
});
