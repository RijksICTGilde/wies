// Inline-edit display partials: a toast on save.

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
