// Behaviour for inline-edit display partials.
//
// Currently: the "Toon meer / Toon minder" toggle on long text fields
// (e.g. Assignment.extra_info). A delegated listener on document
// survives HTMX swaps without rebinding.

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".inline-edit-show-more");
  if (!toggle) return;

  const wrapper = toggle.parentElement;
  if (!wrapper) return;
  // Template uses `inline-edit-long-text__*` for the value spans
  // (the toggle button itself uses `inline-edit-show-more__*`).
  const truncated = wrapper.querySelector(".inline-edit-long-text__truncated");
  const full = wrapper.querySelector(".inline-edit-long-text__full");
  const icon = toggle.querySelector(".inline-edit-show-more__icon");
  const label = toggle.querySelector(".inline-edit-show-more__label");
  if (!truncated || !full || !icon || !label) return;

  const expanded = full.hidden === false;
  truncated.hidden = !expanded;
  full.hidden = expanded;
  icon.textContent = expanded ? "+" : "−";
  label.textContent = expanded ? "Toon meer" : "Toon minder";
});
