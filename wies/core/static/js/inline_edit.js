// Inline-edit display partials: a toast on save.

let savedToast = null;

// The view sets HX-Trigger-After-Swap: inline-edit-saved on the response.
document.addEventListener("inline-edit-saved", (e) => {
  const label = e.detail?.label;
  // A new one instead of update(): live_region.js announces a notification
  // when it enters the document, and identical ones must not stack.
  savedToast?.dismiss();
  savedToast = customElements.get("nldd-notification").show({
    variant: "success",
    // Editable labels arrive capitalised ("Periode"), so the label leads.
    text: label ? `${label} opgeslagen` : "Wijziging opgeslagen",
  });
});
