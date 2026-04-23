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
  const truncated = wrapper.querySelector(".inline-edit-show-more__truncated");
  const full = wrapper.querySelector(".inline-edit-show-more__full");
  const icon = toggle.querySelector(".inline-edit-show-more__icon");
  const label = toggle.querySelector(".inline-edit-show-more__label");
  if (!truncated || !full || !icon || !label) return;

  const expanded = full.hidden === false;
  truncated.hidden = !expanded;
  full.hidden = expanded;
  icon.textContent = expanded ? "+" : "−";
  label.textContent = expanded ? "Toon meer" : "Toon minder";
});
