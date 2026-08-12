// Behaviour for inline-edit display partials: a toast on save, and the
// "Toon meer / Toon minder" toggle on long text fields. Both use delegated
// listeners so they survive HTMX swaps.

function showSavedToast(label) {
  // nldd-notification moves itself into the shared region and runs its own
  // timer, so where it is appended does not matter; ui_handlers.js removes it
  // on `dismiss`. Replacing the previous one keeps a screen that saves several
  // fields in a row from stacking identical messages, and restarts the clock.
  document
    .querySelectorAll("nldd-notification[data-wies-saved]")
    .forEach((el) => el.remove());

  const toast = document.createElement("nldd-notification");
  toast.setAttribute("variant", "success");
  // Editable labels arrive capitalised ("Periode"), so the label leads.
  toast.setAttribute(
    "text",
    label ? `${label} opgeslagen` : "Wijziging opgeslagen",
  );
  toast.setAttribute("data-wies-saved", "");
  document.body.appendChild(toast);
}

// The view sets HX-Trigger-After-Swap: inline-edit-saved on the response.
document.addEventListener("inline-edit-saved", (e) =>
  showSavedToast(e.detail?.label),
);

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".inline-edit-show-more");
  if (!toggle) return;

  const wrapper = toggle.parentElement;
  if (!wrapper) return;
  // The toggle is an nldd-button, so its text and icon are set via attributes.
  const truncated = wrapper.querySelector(".inline-edit-long-text__truncated");
  const full = wrapper.querySelector(".inline-edit-long-text__full");
  if (!truncated || !full) return;

  const expanded = full.hidden === false;
  truncated.hidden = !expanded;
  full.hidden = expanded;
  toggle.setAttribute("text", expanded ? "Toon meer" : "Toon minder");
  toggle.setAttribute("start-icon", expanded ? "chevron-down" : "chevron-up");
});
