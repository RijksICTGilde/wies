// Inline-edit display partials: a toast on save and the "Toon meer" toggle.

function showSavedToast(label) {
  // nldd-notification relocates itself and runs its own timer. Replacing the
  // previous one stops identical messages from stacking.
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
